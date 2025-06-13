from fastapi import APIRouter, UploadFile, File, Form
from api.document.schemas.document_upload import DocumentUploadResponse
from api.document.crud.document import save_document_locally

router = APIRouter()

@router.post("/api/document", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_id: str = Form(...),
    project_id: str = Form(...),
    name: str = Form(...)
):
    content = await file.read()
    result = save_document_locally(content, document_id, project_id, name)
    return {
        "message": "파일 처리 완료",
        "file_path": str(result["project_path"])
    }
