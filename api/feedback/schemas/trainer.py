# ai/api/feedback/schemas/feedback.py
from typing import List

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
                "overall_pass_rate": 72.5,
                "total_participants": 20,
            }
        }
    }


class DocumentPerformance(BaseModel):
    """문서별 성과 분석"""

    document_name: str = Field(description="문서명")
    average_correct_rate: float = Field(description="평균 정답률", ge=0.0, le=100.0)
    comment: str = Field(description="문서별 코멘트")


class FeedbackGenerationResponse(BaseModel):
    """피드백 생성 응답 스키마"""

    exam_goal: str = Field(description="시험 목표")
    performance_by_document: List[DocumentPerformance] = Field(
        description="문서별 성과 분석"
    )
    strengths: List[str] = Field(description="강점 분석")
    weaknesses: List[str] = Field(description="약점 분석")
    improvement_points: str = Field(description="개선점")
    suggested_topics: List[str] = Field(description="추천 학습 주제")
    overall_evaluation: str = Field(description="종합 평가")

    model_config = {
        "json_schema_extra": {
            "example": {
                "exam_goal": "효율적인 프론트엔드 개발 환경 구축 역량을 확인합니다.",
                "performance_by_document": [
                    {
                        "document_name": "개발 Process 흐름도_sample",
                        "average_correct_rate": 79.42,
                        "comment": "DevOps 전반에 대한 이해 수준이 높으며 안정적인 흐름 파악",
                    }
                ],
                "strengths": [
                    "#CI/CD와 #배포 관련 문항에서 높은 정답률을 기록하며 DevOps 파이프라인의 핵심 개념을 잘 이해하고 있음"
                ],
                "weaknesses": [
                    "#빌드도구(Webpack), #환경변수(.env), #패키지관리(npm)와 같은 기초 개발환경에 대한 이해 부족이 드러남"
                ],
                "improvement_points": "기초 개발환경인 빌드 도구, 환경 변수, 패키지 관리 개념을 명확히 정리하고 실습 중심으로 학습을 강화하며, 주관식 문항에서는 핵심 용어를 포함한 구체적 설명력을 높이는 연습이 필요합니다.",
                "suggested_topics": [
                    "패키지 보안 취약점 탐지 도구인 npm audit의 사용법과 보안 문제 해결 방법에 대한 문제를 추가 생성하기."
                ],
                "overall_evaluation": "본 시험은 응시자의 전반적인 프론트엔드 실무 역량을 파악하는 데 유의미한 결과를 제공하였습니다...",
            }
        }
    }
