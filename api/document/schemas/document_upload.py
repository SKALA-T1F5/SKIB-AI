from pydantic import BaseModel

class DocumentMetaRequest(BaseModel):
    document_id: str
    project_id: str
    name: str

class DocumentUploadResponse(BaseModel):
    message: str
    file_path: str
