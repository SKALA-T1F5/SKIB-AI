# api/document/schemas/document_summary.py
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class DocumentContentAnalysisBase(BaseModel):
    """문서 내용 분석 기본 정보"""

    summary: str = Field(..., description="문서 요약")
    main_topics: List[str] = Field(default_factory=list, description="주요 주제")
    key_concepts: List[str] = Field(default_factory=list, description="핵심 개념")
    technical_terms: List[str] = Field(default_factory=list, description="기술 용어")


class SummaryByDocumentResponse(BaseModel):
    """SpringBoot 호환 요약 DTO"""

    summary: str
    keywords: List[str]  # main_topics + key_concepts 조합
    document_id: int


class DocumentSummaryRequest(BaseModel):
    """문서 요약 요청"""

    document_id: int


class DocumentSummaryResponse(BaseModel):
    """문서 요약 응답 (FastAPI 내부용 - 상세)"""

    document_id: int
    content_analysis: DocumentContentAnalysisBase


class DocumentSummaryListResponse(BaseModel):
    """문서 요약 목록 응답 (SpringBoot 호환)"""

    summaries: List[DocumentSummaryResponse]
    total_count: int


# 전역 결과 저장소
document_result: Dict[int, Any] = {}


def set_result(doc_id: int, result: Any):
    """문서 ID에 해당하는 결과를 저장"""
    document_result[doc_id] = result


def get_result(doc_id: int) -> Any:
    """문서 ID에 해당하는 결과를 반환. 없으면 None"""
    return document_result.get(doc_id)


def cleanup_result(doc_id: int):
    """문서 ID에 해당하는 결과 삭제"""
    document_result.pop(doc_id, None)
