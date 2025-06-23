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


@router.get("/summary/{documentId}", response_model=SummaryByDocumentResponse)
async def get_document_summary(documentId: int):
    """
    상태 기반으로 요약 정보 조회
    """
    try:
        status = get_status(documentId)
        logger.debug(f"Document {documentId} status: {status}")

        # 1. 처리 중 -> 202 Accepted
        if status == StatusEnum.PROCESSING:
            raise HTTPException(
                status_code=202, detail="Document is still being processed"
            )

        # 2. 실패 -> 500 Error
        if status == StatusEnum.FAILED:
            raise HTTPException(status_code=500, detail="Document processing failed")

        # 3. 완료 -> 200 OK + 데이터
        if status == StatusEnum.DONE:
            result = get_result(documentId)
            if result:
                return SummaryByDocumentResponse(
                    summary=result.get("summary", ""),
                    keywords=result.get("keywords", []),
                    documentId=documentId,
                )
            else:
                raise HTTPException(status_code=404, detail="Summary result not found")

        # 4. 상태 없음 -> 404
        raise HTTPException(status_code=404, detail="Document not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summary retrieval failed for document {documentId}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Summary retrieval failed: {str(e)}"
        )


async def process_document_background(
    file_path: str, documentId: int, project_id: int, filename: str
):
    """백그라운드 처리 - 간단한 상태 관리"""
    try:
        logger.info(f"Starting background processing for documentId: {documentId}")

        # Pipeline 실행
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
                "documentId": documentId,
                "project_id": project_id,
                "filename": filename,
            }
        )

        # 결과 처리
        if result.get("processing_status") == "completed":
            content_analysis = result.get("content_analysis", {})

            # SpringBoot 형식으로 변환
            main_topics = content_analysis.get("main_topics", [])
            key_concepts = content_analysis.get("key_concepts", [])
            keywords = (main_topics + key_concepts)[:10]

            summary_data = {
                "summary": content_analysis.get("summary", ""),
                "keywords": keywords,
                "documentId": documentId,
            }

            # 1. 결과 저장
            set_result(documentId, summary_data)
            set_status(documentId, StatusEnum.DONE)

            # TODO SpringBoot 연결 후 확인 필요
            # # 2. SpringBoot에 알림
            success = await notify_springboot_completion(documentId, summary_data)

            if success:
                # 3. 완료 상태로 변경
                set_status(documentId, StatusEnum.DONE)
                logger.info(f"✅ Processing completed for documentId: {documentId}")
            else:
                set_status(documentId, StatusEnum.FAILED)
                logger.error(f"SpringBoot 알림 실패: documentId: {documentId}")
        else:
            # 실패 처리
            set_status(documentId, StatusEnum.FAILED)
            logger.error(f"❌ Pipeline failed for documentId: {documentId}")

    except Exception as e:
        # 예외 발생 시 실패 상태
        set_status(documentId, StatusEnum.FAILED)
        logger.error(
            f"""Exception in background processing for
                documentId {documentId}: {str(e)}"""
        )


async def notify_springboot_completion(documentId: int, summary_data: Dict) -> bool:
    """SpringBoot에 처리 완료 알림"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"https://skib-backend.skala25a.project.skala-ai.com/api/document/summary/{documentId}",
                json=summary_data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                logger.info(f"✅ SpringBoot 알림 성공: documentId={documentId}")
                return True
            else:
                logger.error(f"SpringBoot 알림 실패: {response.status_code}")
                return False

    except Exception as e:
        logger.error(f"SpringBoot 알림 중 오류: {str(e)}")
        return False
