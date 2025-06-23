from fastapi import APIRouter

from api.document.schemas.document_status import DocumentStatusResponse, get_status

router = APIRouter(prefix="/api/document", tags=["Document"])


@router.get("/status/{documentId}", response_model=DocumentStatusResponse)
def get_document_status(documentId: int):
    return DocumentStatusResponse(documentId=documentId, status=get_status(documentId))
