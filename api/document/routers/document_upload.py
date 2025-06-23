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


from fastapi import Form


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_id: int = Form(...),
    project_id: int = Form(...),
    name: str = Form(...),
):
    try:
        # ✅ 직접 매핑하여 Pydantic 객체 생성
        metadata = DocumentUploadMetaRequest(
            document_id=document_id, project_id=project_id, name=name
        )

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
        logger.exception("🔥 [UPLOAD ERROR] 문서 업로드 중 예외 발생")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
