from pydantic import BaseModel


class DocumentUploadMetaRequest(BaseModel):
    document_id: int
    project_id: int
    name: str


class DocumentUploadResponse(BaseModel):
    message: str
    file_path: str
