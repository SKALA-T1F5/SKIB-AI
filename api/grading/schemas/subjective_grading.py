from typing import List

from pydantic import BaseModel, Field


class GradingCriterion(BaseModel):
    score: float = Field(
        ..., description="채점 기준에 해당하는 점수 (예: 1.0, 0.5, 0.0)"
    )
    criteria: str = Field(..., description="채점 기준 설명")
    example: str = Field(..., description="기준에 해당하는 예시 답변")
    note: str = Field(..., description="해당 기준을 선택한 이유나 주의사항")


class SubjectiveGradingRequest(BaseModel):
    question_id: str = Field(..., alias="questionId", description="문제의 고유 ID")
    response: str = Field(..., description="사용자가 작성한 주관식 답변")
    grading_criteria: List[GradingCriterion] = Field(
        ..., description="채점을 위한 기준 리스트"
    )

    model_config = {"populate_by_name": True}


class SubjectiveGradingResponse(BaseModel):
    question_id: str = Field(..., description="문제의 고유 ID")
    score: float = Field(..., description="선택된 기준에 따른 최종 점수")
