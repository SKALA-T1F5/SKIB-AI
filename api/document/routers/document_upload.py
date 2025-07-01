# api/document/routers/document_upload.py (리팩토링)
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
from config.tasks import process_document_task
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

        process_document_task.delay(
            task_id=task_id,
            file_path=str(result["project_path"]),
            documentId=metadata.documentId,
            project_id=metadata.project_id,
            filename=metadata.name,
        )

        return DocumentUploadResponse(
            file_path=str(result["project_path"]),
            message="파일 업로드 완료. 처리가 진행 중입니다.",
        )

    except Exception as e:
        logger.exception("🔥 [UPLOAD ERROR] 문서 업로드 중 예외 발생")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# @router.get("/upload/progress/{task_id}")
# async def get_document_processing_progress(task_id: str):
#     """문서 처리 진행률 조회"""
#     try:
#         from api.websocket.services.progress_tracker import get_task_progress

#         progress_data = await get_task_progress(task_id)

#         if not progress_data:
#             raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

#         return {
#             "task_id": progress_data.task_id,
#             "status": progress_data.status.value,
#             "progress": progress_data.progress,
#             "message": progress_data.message,
#             "updated_at": progress_data.updated_at.isoformat(),
#         }

#     except HTTPException:
#         raise
#     except Exception as e:
#         logger.error(f"❌ 문서 진행률 조회 실패 ({task_id}): {e}")
#         raise HTTPException(status_code=500, detail="Progress retrieval failed")
