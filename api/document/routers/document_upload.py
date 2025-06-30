# api/document/routers/document_upload.py (리팩토링)
import asyncio
import logging
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.document.crud.document import save_document_locally
from api.document.schemas.document_status import DocumentProcessingStatus
from api.document.schemas.document_upload import (
    DocumentUploadMetaRequest,
    DocumentUploadResponse,
)
from api.websocket.services.springboot_notifier import notify_document_progress
from utils.naming import filename_to_collection

router = APIRouter(prefix="/api/document", tags=["Document"])
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_id: int = Form(...),
    project_id: int = Form(...),
    name: str = Form(...),
):
    """
    비동기 문서 업로드 - 즉시 task_id 반환, 백그라운드에서 처리
    """
    try:
        # Task ID 생성
        task_id = str(uuid4())

        new_name = filename_to_collection(name)

        # 메타데이터 객체 생성
        metadata = DocumentUploadMetaRequest(
            documentId=document_id, project_id=project_id, name=new_name
        )

        logger.info(
            f"Document upload started: {metadata.documentId}, task_id: {task_id}"
        )

        # 파일 저장
        content = await file.read()
        result = save_document_locally(
            content, metadata.documentId, metadata.project_id, metadata.name
        )

        # 업로드 완료 알림
        await notify_document_progress(
            task_id=task_id,
            document_id=metadata.documentId,
            status=DocumentProcessingStatus.UPLOAD_COMPLETED,
        )

        # 백그라운드에서 문서 처리 실행
        asyncio.create_task(
            background_document_processing(
                task_id=task_id,
                file_path=result["project_path"],
                documentId=metadata.documentId,
                project_id=metadata.project_id,
                filename=metadata.name,
            )
        )

        return DocumentUploadResponse(
            file_path=str(result["project_path"]),
            message="파일 업로드 완료. 처리가 진행 중입니다.",
        )

    except Exception as e:
        logger.exception("🔥 [UPLOAD ERROR] 문서 업로드 중 예외 발생")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def background_document_processing(
    task_id: str, file_path: str, documentId: int, project_id: int, filename: str
):
    """백그라운드에서 문서 처리 수행"""
    try:
        from src.pipelines.document_processing.pipeline import (
            DocumentProcessingPipeline,
        )

        # 전처리 시작 알림
        await notify_document_progress(
            task_id=task_id,
            document_id=documentId,
            status=DocumentProcessingStatus.PREPROCESSING,
        )

        pipeline = DocumentProcessingPipeline(
            config={
                "enable_vectordb": True,
                "timeout_seconds": 600,
                "max_retries": 3,
            }
        )

        # 파이프라인 실행
        result = await pipeline.run(
            {
                "document_path": file_path,
                "documentId": documentId,
                "project_id": project_id,
                "filename": filename,
            }
        )

        if result.get("processing_status") == "completed":
            # 요약 생성 알림
            await notify_document_progress(
                task_id=task_id,
                document_id=documentId,
                status=DocumentProcessingStatus.SUMMARIZING,
            )

            # 결과 처리
            content_analysis = result.get("content_analysis", {})
            main_topics = content_analysis.get("main_topics", [])
            key_concepts = content_analysis.get("key_concepts", [])
            keywords = (main_topics + key_concepts)[:10]

            summary_data = {
                "summary": content_analysis.get("summary", ""),
                "keywords": keywords,
                "document_id": documentId,
                "name": result.get("filename", ""),
            }

            # SpringBoot에 요약 데이터 전송 (기존 API 사용)
            success = await notify_springboot_summary_completion(
                documentId, summary_data
            )

            if success:
                # 완료 알림
                await notify_document_progress(
                    task_id=task_id,
                    document_id=documentId,
                    status=DocumentProcessingStatus.SUMMARY_COMPLETED,
                )
                logger.info(f"✅ 문서 처리 완료: {documentId}")
            else:
                # 실패 알림
                await notify_document_progress(
                    task_id=task_id,
                    document_id=documentId,
                    status=DocumentProcessingStatus.FAILED,
                    error_code="SUMMARY_UPLOAD_FAILED",
                )
        else:
            # 파이프라인 실패
            await notify_document_progress(
                task_id=task_id,
                document_id=documentId,
                status=DocumentProcessingStatus.FAILED,
                error_code="PROCESSING_FAILED",
            )

    except Exception as e:
        # 예외 발생시 실패 알림
        await notify_document_progress(
            task_id=task_id,
            document_id=documentId,
            status=DocumentProcessingStatus.FAILED,
            error_code="PROCESSING_EXCEPTION",
        )
        logger.error(f"❌ 백그라운드 문서 처리 실패: {documentId} - {e}")


async def notify_springboot_summary_completion(
    documentId: int, summary_data: dict
) -> bool:
    """SpringBoot에 요약 완료 알림 (기존 API 사용)"""
    try:
        import httpx

        from config.settings import settings

        url = f"{settings.backend_url}/api/document/summary/{documentId}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(
                url,
                json=summary_data,
                headers={"Content-Type": "application/json"},
            )

        if response.status_code == 200:
            logger.info(f"✅ SpringBoot 요약 알림 성공: documentId={documentId}")
            return True
        else:
            logger.error(f"🚫 SpringBoot 요약 알림 실패: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ SpringBoot 요약 알림 예외: {e}")
        return False


@router.get("/upload/progress/{task_id}")
async def get_document_processing_progress(task_id: str):
    """문서 처리 진행률 조회"""
    try:
        from api.websocket.services.progress_tracker import get_task_progress

        progress_data = await get_task_progress(task_id)

        if not progress_data:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        return {
            "task_id": progress_data.task_id,
            "status": progress_data.status.value,
            "progress": progress_data.progress,
            "message": progress_data.message,
            "updated_at": progress_data.updated_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 문서 진행률 조회 실패 ({task_id}): {e}")
        raise HTTPException(status_code=500, detail="Progress retrieval failed")
