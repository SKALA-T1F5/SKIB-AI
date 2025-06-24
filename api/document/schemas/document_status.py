from enum import Enum
from typing import Dict

from pydantic import BaseModel


class StatusEnum(str, Enum):
    PROCESSING = "전처리 중입니다"
    DONE = "완료되었습니다"
    FAILED = "실패하였습니다"


class DocumentStatusResponse(BaseModel):
    documentId: int
    status: StatusEnum


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
