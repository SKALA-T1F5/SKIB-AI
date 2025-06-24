from fastapi import APIRouter, HTTPException

from api.grading.schemas.subjective_grading import (
    SubjectiveGradingRequest,
    SubjectiveGradingResponse,
)
from src.agents.subjective_grader.agent import subjective_grader

router = APIRouter(prefix="/api/grading", tags=["Grading"])


@router.post("/subjective", response_model=SubjectiveGradingResponse)
async def grade_subjective_answer(payload: SubjectiveGradingRequest):
    """
    사용자 답변과 기준을 바탕으로 OpenAI Agent를 통해 채점 수행
    """
    if not payload.grading_criteria:
        raise HTTPException(status_code=400, detail="채점 기준이 존재하지 않습니다.")

    try:
        score = await subjective_grader(payload.user_answer, payload.grading_criteria)
        # score = await subjective_grader(payload.user_answer, payload.grading_criteria)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"채점 실패: {str(e)}")

    return SubjectiveGradingResponse(
        question_id=payload.question_id,
        score=score,
    )
