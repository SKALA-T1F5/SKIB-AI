from fastapi import APIRouter, UploadFile, File, Depends
from api.document.schemas.document_upload import DocumentUploadResponse, DocumentMetaRequest
from api.document.crud.document import save_document_locally

router = APIRouter()

@router.post("/api/document", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    metadata: DocumentMetaRequest = Depends()
):
    content = await file.read()
    result = save_document_locally(content, metadata.document_id, metadata.project_id, metadata.name)
    return {
        "message": "파일 처리 완료",
        "file_path": str(result["project_path"])
    }

