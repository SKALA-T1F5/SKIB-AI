from typing import List

from pydantic import BaseModel, Field

from api.document.schemas.document_summary import SummaryByDocumentResponse
from api.question.schemas.question import DifficultyLevel


class TestPlanRequest(BaseModel):
    project_id: int = Field(..., alias="projectId", description="프로젝트 ID")
    user_input: str = Field(..., alias="userInput", description="사용자 입력")
    document_summaries: List[SummaryByDocumentResponse] = Field(
        ..., alias="documentSummaries", description="문서 요약 목록"
    )

    model_config = {"populate_by_name": True}


class TestPlanByDocument(BaseModel):
    documentId: int = Field(..., description="문서 ID")
    document_name: str = Field(..., alias="documentName", description="문서 이름")
    keywords: List[str] = Field(..., description="키워드 목록")
    configured_objective_count: int = Field(
        ..., alias="configuredObjectiveCount", description="객관식 문항 수"
    )
    configured_subjective_count: int = Field(
        ..., alias="configuredSubjectiveCount", description="주관식 문항 수"
    )

    model_config = {"populate_by_name": True}


class TestPlanResponse(BaseModel):
    name: str
    summary: str = Field(..., description="테스트 요약")
    difficulty_level: DifficultyLevel = Field(
        alias="difficultyLevel", description="난이도"
    )
    limited_time: int = Field(alias="limitedTime", description="제한 시간 (분)")
    pass_score: int = Field(alias="passScore", description="통과 점수 (%)")
    is_retake: bool = Field(alias="isRetake", description="재응시 여부")
    document_configs: List[TestPlanByDocument] = Field(
        alias="documentConfigs", description="문서별 질문 구성"
    )

    model_config = {"populate_by_name": True}  # v2 방식
