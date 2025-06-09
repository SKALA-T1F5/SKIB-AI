from fastapi import APIRouter, UploadFile, File, Form
from api.document.schemas.document_upload import DocumentMetaRequest
from api.document.crud.document_crud import save_file_locally
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/api/document")
async def upload_document(
    document_id: str = Form(...),
    project_id: str = Form(...),
    name: str = Form(...),
    file: UploadFile = File(...)
):
    # 파일 읽기
    contents = await file.read()
    filename = f"{document_id}_{file.filename}"

    try:
        path = save_file_locally(contents, filename)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    return {
        "message": "File uploaded successfully",
        "file_path": path,
        "meta": {
            "document_id": document_id,
            "project_id": project_id,
            "name": name
        }
    }
