import logging
from typing import Dict

import httpx
from fastapi import APIRouter, HTTPException

from api.document.schemas.document_status import StatusEnum, get_status, set_status
from api.document.schemas.document_summary import (
    SummaryByDocumentResponse,
    get_result,
    set_result,
)
from src.pipelines.document_processing.pipeline import DocumentProcessingPipeline

router = APIRouter(prefix="/api/document", tags=["Document"])
logger = logging.getLogger(__name__)


def build_summary_response(document_id: int) -> SummaryByDocumentResponse:
    """
    상태 기반으로 SummaryByDocumentResponse 객체 생성
    """
    status = get_status(document_id)
    logger.debug(f"Document {document_id} status: {status}")

    if status == StatusEnum.PROCESSING:
        raise HTTPException(status_code=202, detail="Document is still being processed")

    if status == StatusEnum.FAILED:
        raise HTTPException(status_code=500, detail="Document processing failed")

    if status == StatusEnum.DONE:
        result = get_result(document_id)
        if result:
            return SummaryByDocumentResponse(
                summary=result.get("summary", ""),
                keywords=result.get("keywords", []),
                document_id=document_id,
            )
        else:
            raise HTTPException(status_code=404, detail="Summary result not found")

    raise HTTPException(status_code=404, detail="Document not found")


@router.get("/summary/{document_id}", response_model=SummaryByDocumentResponse)
async def get_document_summary(document_id: int):
    """
    상태 기반으로 요약 정보 조회 (API용)
    """
    try:
        return build_summary_response(document_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summary retrieval failed for document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Summary retrieval failed: {str(e)}"
        )


async def process_document_background(
    file_path: str, document_id: int, project_id: int, filename: str
):
    """
    문서 전처리 백그라운드 실행
    """
    try:
        logger.info(f"📄 Starting background processing for document_id: {document_id}")

        pipeline = DocumentProcessingPipeline(
            config={
                "enable_vectordb": True,
                "timeout_seconds": 600,
                "max_retries": 3,
            }
        )

        result = await pipeline.run(
            {
                "document_path": file_path,
                "document_id": document_id,
                "project_id": project_id,
                "filename": filename,
            }
        )

        if result.get("processing_status") == "completed":
            content_analysis = result.get("content_analysis", {})
            main_topics = content_analysis.get("main_topics", [])
            key_concepts = content_analysis.get("key_concepts", [])
            keywords = (main_topics + key_concepts)[:10]

            summary_data = {
                "summary": content_analysis.get("summary", ""),
                "keywords": keywords,
                "document_id": document_id,
            }

            set_result(document_id, summary_data)
            set_status(document_id, StatusEnum.DONE)

            try:
                # ✨ 여기서 직접 SummaryByDocumentResponse 생성
                summary_response = build_summary_response(document_id)

                success = await notify_springboot_completion(
                    document_id, summary_response.dict()
                )

                if success:
                    set_status(document_id, StatusEnum.DONE)
                    logger.info(
                        f"✅ Processing completed for document_id: {document_id}"
                    )
                else:
                    set_status(document_id, StatusEnum.FAILED)
                    logger.error(f"🚫 SpringBoot 알림 실패: document_id: {document_id}")
            except Exception as e:
                set_status(document_id, StatusEnum.FAILED)
                logger.error(f"🚫 build_summary_response 실패: {str(e)}")

        else:
            set_status(document_id, StatusEnum.FAILED)
            logger.error(f"❌ Pipeline failed for document_id: {document_id}")

    except Exception as e:
        set_status(document_id, StatusEnum.FAILED)
        logger.error(
            f"❌ Exception in background processing for document_id {document_id}: {str(e)}"
        )


async def notify_springboot_completion(document_id: int, summary_data: Dict) -> bool:
    try:
        logger.info(f"📡 전송 대상 데이터: {summary_data}")

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"https://skib-backend.skala25a.project.skala-ai.com/api/document/summary/{document_id}",
                json=summary_data,
                headers={"Content-Type": "application/json"},
            )

            logger.info(f"📡 SpringBoot 응답 코드: {response.status_code}")
            logger.info(f"📡 SpringBoot 응답 내용: {response.text}")

            if response.status_code == 200:
                logger.info(f"✅ SpringBoot 알림 성공: document_id={document_id}")
                return True
            else:
                logger.error(
                    f"🚫 SpringBoot 알림 실패: 상태 코드 {response.status_code}"
                )
                return False

    except Exception as e:
        logger.error(f"❌ SpringBoot 알림 중 오류 발생: {str(e)}")
        return False
