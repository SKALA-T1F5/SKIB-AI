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

    # test_id: str = Field(description="테스트 ID")
    # test_title: str = Field(description="테스트 제목")
    test_summary: str = Field(
        description="앞서 시험 생성 시에 정의한 시험 요약 및 목표"
    )
    questions: List[TrainerFeedbackItemDto] = Field(description="문제별 피드백 데이터")

    model_config = {
        "json_schema_extra": {
            "example": {
                "test_summary": "프론트엔드 개발 환경 구축 및 DevOps 파이프라인 이해도를 평가합니다.",
                "questions": [
                    {
                        "questionId": "q1",
                        "questionNumber": 1,
                        "documentId": "doc1",
                        "documentName": "개발 Process 흐름도_sample",
                        "questionText": "CI/CD 파이프라인의 핵심 구성요소는?",
                        "difficulty": "MEDIUM",
                        "type": "MULTIPLE_CHOICE",
                        "answer": "Build, Test, Deploy",
                        "tags": ["CI/CD", "배포"],
                        "correctRate": 85.5,
                    }
                ],
            }
        }
    }


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

    model_config = {
        "populate_by_name": True,
        "json_schema_extra": {
            "example": {
                "examGoal": "효율적인 프론트엔드 개발 환경 구축 역량 확인",
                "performanceByDocument": [
                    {
                        "documentName": "Aiper Front 개발환경 가이드",
                        "averageCorrectRate": 93.9,
                        "comment": "개발 환경 구축 및 최적화 기법에 대한 이해도가 매우 높으며, 실무 적용 능력이 뛰어납니다.",
                    }
                ],
                "insights": [
                    {
                        "type": "strength",
                        "text": "'#프론트엔드개발환경' 구축 및 최적화 전략 전반에 대한 높은 이해도",
                    },
                    {
                        "type": "weakness",
                        "text": "개발 환경 구축 시 자주 발생하는 '#문제해결' 경험은 있으나, 구체적인 사례 기반 학습은 보완 가능",
                    },
                ],
                "improvementPoints": "실제 개발 환경에서 발생할 수 있는 다양한 장애 상황에 대한 대처 능력 향상을 위해 구체적인 문제 해결 사례를 학습하고 공유하는 것이 좋습니다.",
                "suggestedTopics": [
                    "다양한 프론트엔드 빌드 도구(Webpack, Vite 등) 비교 및 설정 실습"
                ],
                "overallEvaluation": "프론트엔드 개발 환경 구축 및 최적화에 대한 이해도가 매우 높아 프로젝트 수행에 즉시 투입 가능합니다.",
                "projectReadiness": "Excellent",
            }
        },
    }
