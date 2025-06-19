from fastapi import APIRouter

from api.document.schemas.document_status import DocumentStatusResponse, get_status

router = APIRouter(prefix="/api/document", tags=["Document"])


@router.get("/status/{document_id}", response_model=DocumentStatusResponse)
def get_document_status(document_id: int):
    return DocumentStatusResponse(
        document_id=document_id, status=get_status(document_id)
    )
