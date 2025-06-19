import logging
from typing import Dict

import httpx
from api.document.status import Status, get_result, get_status, set_result, set_status
from fastapi import APIRouter, HTTPException

from api.document.schemas.document_summary import SummaryByDocumentResponse
from src.pipelines.document_processing.pipeline import DocumentProcessingPipeline

router = APIRouter(prefix="/api/document", tags=["Document"])
logger = logging.getLogger(__name__)


@router.get("/summary/{document_id}", response_model=SummaryByDocumentResponse)
async def get_document_summary(document_id: int):
    """
    상태 기반으로 요약 정보 조회
    """
    try:
        status = get_status(document_id)
        logger.debug(f"Document {document_id} status: {status}")

        # 1. 처리 중 -> 202 Accepted
        if status == Status.PROCESSING:
            raise HTTPException(
                status_code=202, detail="Document is still being processed"
            )

        # 2. 실패 -> 500 Error
        if status == Status.FAILED:
            raise HTTPException(status_code=500, detail="Document processing failed")

        # 3. 완료 -> 200 OK + 데이터
        if status == Status.DONE:
            result = get_result(document_id)
            if result:
                return SummaryByDocumentResponse(
                    summary=result.get("summary", ""),
                    keywords=result.get("keywords", []),
                    document_id=document_id,
                )
            else:
                raise HTTPException(status_code=404, detail="Summary result not found")

        # 4. 상태 없음 -> 404
        raise HTTPException(status_code=404, detail="Document not found")

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
    """백그라운드 처리 - 간단한 상태 관리"""
    try:
        logger.info(f"Starting background processing for document_id: {document_id}")

        # Pipeline 실행
        pipeline = DocumentProcessingPipeline(
            config={
                "enable_vectordb": False,
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
                "document_id": document_id,
            }

            # 1. 결과 저장
            set_result(document_id, summary_data)

            # 2. SpringBoot에 알림
            success = await notify_springboot_completion(document_id, summary_data)

            if success:
                # 3. 완료 상태로 변경
                set_status(document_id, Status.DONE)
                logger.info(f"✅ Processing completed for document_id: {document_id}")
            else:
                set_status(document_id, Status.FAILED)
                logger.error(f"SpringBoot 알림 실패: document_id: {document_id}")
        else:
            # 실패 처리
            set_status(document_id, Status.FAILED)
            logger.error(f"❌ Pipeline failed for document_id: {document_id}")

    except Exception as e:
        # 예외 발생 시 실패 상태
        set_status(document_id, Status.FAILED)
        logger.error(
            f"""Exception in background processing for
                document_id {document_id}: {str(e)}"""
        )


async def notify_springboot_completion(document_id: int, summary_data: Dict) -> bool:
    """SpringBoot에 처리 완료 알림"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"http://localhost:8080/api/document/summary/{document_id}",
                json=summary_data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                logger.info(f"✅ SpringBoot 알림 성공: document_id={document_id}")
                return True
            else:
                logger.error(f"SpringBoot 알림 실패: {response.status_code}")
                return False

    except Exception as e:
        logger.error(f"SpringBoot 알림 중 오류: {str(e)}")
        return False
