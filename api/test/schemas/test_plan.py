from typing import List

from pydantic import BaseModel

from api.document.schemas.document_summary import SummaryByDocumentResponse
from api.question.schemas.question import DifficultyLevel


class TestPlanRequest(BaseModel):
    project_id: int
    user_input: str
    document_summaries: List[SummaryByDocumentResponse]


class TestPlanByDocument(BaseModel):
    document_id: int
    keywords: List[str]
    recommended_objective: int
    recommended_subjective: int


class TestPlanResponse(BaseModel):
    name: str
    test_summary: str
    difficulty_level: DifficultyLevel
    limited_time: int  # 분 단위
    pass_score: int  # 통과 점수 (%)
    is_retake: bool  # 재응시 여부
    document_configs: List[TestPlanByDocument]
