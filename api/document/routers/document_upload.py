# api/document/routers/document_upload.py
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from api.document.crud.document import save_document_locally
from api.document.routers.document_summary import process_document_background
from api.document.schemas.document_status import StatusEnum, set_status
from api.document.schemas.document_upload import (
    DocumentUploadMetaRequest,
    DocumentUploadResponse,
)

router = APIRouter(prefix="/api/document", tags=["Document"])
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    metadata: DocumentUploadMetaRequest = Depends(),
):
    try:
        # 정상 처리 로직
        set_status(metadata.document_id, StatusEnum.PROCESSING)
        logger.info(
            f"""Document upload started: {metadata.document_id},
                project_id: {metadata.project_id},
                name: {metadata.name}"""
        )

        content = await file.read()
        result = save_document_locally(
            content, metadata.document_id, metadata.project_id, metadata.name
        )

        background_tasks.add_task(
            process_document_background,
            file_path=result["project_path"],
            document_id=metadata.document_id,
            project_id=metadata.project_id,
            filename=metadata.name,
        )

        return DocumentUploadResponse(
            file_path=str(result["project_path"]), message="파일 처리 완료"
        )

    except Exception as e:
        logger.exception("🔥 [UPLOAD ERROR] 문서 업로드 중 예외 발생")  # <-- 여기!
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
