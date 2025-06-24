from fastapi import Form
from pydantic import BaseModel


class DocumentUploadMetaRequest(BaseModel):
    documentId: int = Form(...)
    project_id: int = Form(...)
    name: str = Form(...)


class DocumentUploadResponse(BaseModel):
    message: str
    file_path: str
