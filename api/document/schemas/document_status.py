from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class StatusEnum(str, Enum):
    PROCESSING = "전처리 중입니다"
    DONE = "완료되었습니다"
    FAILED = "실패하였습니다"


class DocumentStatusResponse(BaseModel):
    documentId: int
    status: StatusEnum


class DocumentProcessingStatus(str, Enum):
    """문서 처리 단계"""

    UPLOAD_COMPLETED = "UPLOAD_COMPLETED"  # 업로드 완료
    PREPROCESSING = "PREPROCESSING"  # 전처리 중
    SUMMARIZING = "SUMMARIZING"  # 요약 중
    SUMMARY_COMPLETED = "SUMMARY_COMPLETED"  # 요약 완료
    FAILED = "FAILED"  # 실패


class DocumentStatusUpdateDto(BaseModel):
    """SpringBoot 전송용 문서 상태 업데이트"""

    model_config = ConfigDict(use_enum_values=True)

    documentId: int = Field(..., description="문서 ID")
    status: DocumentProcessingStatus = Field(..., description="현재 처리 단계")


class SpringBootDocumentResponse(BaseModel):
    """SpringBoot 응답"""

    status: str = Field(..., description="응답 상태")
    code: str = Field(..., description="응답 코드")
    message: Optional[str] = Field(default=None, description="응답 메시지")


# 간단한 딕셔너리 하나
document_status: Dict[int, StatusEnum] = {}


def set_status(doc_id: int, status: StatusEnum):
    document_status[doc_id] = status


def get_status(doc_id: int) -> StatusEnum:
    return document_status.get(doc_id, StatusEnum.PROCESSING)


def is_done(doc_id: int) -> bool:
    return document_status.get(doc_id) == StatusEnum.DONE


def cleanup(doc_id: int):
    document_status.pop(doc_id, None)
