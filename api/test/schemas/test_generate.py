from typing import (
    List,
)

from pydantic import BaseModel, Field

from api.question.schemas.question import DifficultyLevel, QuestionResponse
from api.test.schemas.test_plan import TestPlanByDocument

# class TestDocumentConfig(BaseModel):
#     documentId: int = Field(..., alias="documentId", description="문서 ID")
#     keywords: List[str] = Field(..., description="문서 관련 키워드 목록")
#     configured_objective_count: int = Field(
#         ..., alias="configuredObjectiveCount", description="객관식 문항 수"
#     )
#     configured_subjective_count: int = Field(
#         ..., alias="configuredSubjectiveCount", description="주관식 문항 수"
#     )

#     model_config = {"populate_by_name": True}


class TestGenerationRequest(BaseModel):
    name: str = Field(..., description="테스트 이름")
    summary: str = Field(..., description="테스트 요약")
    difficulty_level: DifficultyLevel = Field(
        ..., alias="difficultyLevel", description="난이도"
    )
    limited_time: int = Field(..., alias="limitedTime", description="제한 시간(분)")
    pass_score: int = Field(..., alias="passScore", description="통과 점수(%)")
    is_retake: bool = Field(..., alias="isRetake", description="재응시 여부")
    document_configs: List[TestPlanByDocument] = Field(
        ..., alias="documentConfigs", description="문서별 설정"
    )

    model_config = {"populate_by_name": True}


class TestGenerationResponse(BaseModel):
    """테스트 생성 응답 (문제 목록만 반환)"""

    questions: List[QuestionResponse] = Field(..., description="생성된 문제 목록")
