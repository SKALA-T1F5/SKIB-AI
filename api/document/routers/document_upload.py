# api/document/routers/document_upload.py
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from api.document.crud.document import save_document_locally
from api.document.routers.document_summary import process_document_background
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
    """
    문서 업로드 및 백그라운드 AI 처리 시작

    SpringBoot 호환:
    - Form 데이터로 받음
    - file_path 반환 (SpringBoot가 response.get("file_path") 호출)
    """
    try:
        # 1. 파일 저장
        content = await file.read()
        result = save_document_locally(
            content, metadata.document_id, metadata.project_id, metadata.name
        )

        # 2. 백그라운드에서 AI 처리 시작
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
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
