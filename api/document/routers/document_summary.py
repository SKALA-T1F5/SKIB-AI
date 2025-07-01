import logging

from fastapi import APIRouter, HTTPException

from api.document.schemas.document_status import (
    StatusEnum,
    get_status,
)
from api.document.schemas.document_summary import (
    SummaryByDocumentResponse,
    get_result,
)

router = APIRouter(prefix="/api/document", tags=["Document"])
logger = logging.getLogger(__name__)


# TODO THIS IS NOT USED
@router.get("/summary/{documentId}", response_model=SummaryByDocumentResponse)
async def get_document_summary(documentId: int):
    """
    상태 기반으로 SummaryByDocumentResponse 객체 생성
    """
    try:
        status = get_status(documentId)
        logger.debug(f"Document {documentId} status: {status}")

        if status == StatusEnum.PROCESSING:
            raise HTTPException(
                status_code=202, detail="Document is still being processed"
            )

        if status == StatusEnum.FAILED:
            raise HTTPException(status_code=500, detail="Document processing failed")

        # 3. 완료 -> 200 OK + 데이터
        if status == StatusEnum.DONE:
            result = get_result(documentId)
            if result:
                return SummaryByDocumentResponse(
                    summary=result.get("summary", ""),
                    keywords=result.get("keywords", []),
                    documentId=documentId,
                    name=result.get("document_name", ""),
                )
            else:
                raise HTTPException(status_code=404, detail="Summary result not found")

        raise HTTPException(status_code=404, detail="Document not found")
    except Exception as e:
        logger.error(f"Summary retrieval failed for document {documentId}: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Summary retrieval failed: {str(e)}"
        )
