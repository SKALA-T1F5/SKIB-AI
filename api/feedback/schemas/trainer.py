# ai/api/feedback/schemas/feedback.py
from typing import List, Literal

from pydantic import BaseModel, Field

from api.question.schemas.question import DifficultyLevel, QuestionType


class TrainerFeedbackItemDto(BaseModel):
    """SpringBoot에서 전달받는 문제별 피드백 데이터"""

    question_id: str = Field(alias="questionId")
    question_number: int = Field(alias="questionNumber")
    document_id: str = Field(alias="documentId")
    document_name: str = Field(alias="documentName")
    question_text: str = Field(alias="questionText")
    difficulty: DifficultyLevel
    type: QuestionType
    answer: str
    tags: List[str]
    correct_rate: float = Field(alias="correctRate", ge=0.0, le=100.0)

    model_config = {"populate_by_name": True}  # v2 방식


class FeedbackGenerationRequest(BaseModel):
    """피드백 생성 요청 스키마"""

    test_summary: str = Field(
        ...,
        alias="testSummary",
        description="앞서 시험 생성 시에 정의한 시험 요약 및 목표",
    )
    feedbacks: List[TrainerFeedbackItemDto] = Field(description="문제별 피드백 데이터")

    model_config = {"populate_by_name": True}  # v2 방식


class DocumentPerformance(BaseModel):
    document_name: str = Field(description="문서 이름", alias="documentName")
    average_correct_rate: float = Field(
        description="평균 정답률", alias="averageCorrectRate"
    )
    comment: str = Field(description="해당 문서에 대한 평가")

    model_config = {"populate_by_name": True}  # v2 방식


class Insight(BaseModel):
    type: Literal["strength", "weakness"] = Field(
        description="인사이트 유형 (강점 또는 약점)"
    )
    text: str = Field(description="인사이트 설명")


class FeedbackGenerationResponse(BaseModel):
    """피드백 생성 응답 스키마"""

    exam_goal: str = Field(description="시험 목표", alias="examGoal")
    performance_by_document: List[DocumentPerformance] = Field(
        description="문서별 성과 분석", alias="performanceByDocument"
    )
    insights: List[Insight] = Field(description="강점 및 약점 인사이트")
    improvement_points: str = Field(description="개선점", alias="improvementPoints")
    suggested_topics: List[str] = Field(
        description="추천 학습 주제", alias="suggestedTopics"
    )
    overall_evaluation: str = Field(description="종합 평가", alias="overallEvaluation")
    project_readiness: str = Field(
        description="프로젝트 투입 준비도", alias="projectReadiness"
    )
    model_config = {"populate_by_name": True}  # v2 방식
