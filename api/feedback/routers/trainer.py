# ai/api/feedback/routers/feedback_generation.py
import logging

from fastapi import APIRouter, HTTPException, status

from api.feedback.schemas.trainer import (
    FeedbackGenerationRequest,
    FeedbackGenerationResponse,
)
from src.agents.test_feedback.agent import test_feedback

# 로깅 설정
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["Feedback Generation"])


# TODO: 에이전트 연동 구현 완료 후 주석 해제 및 테스트 예정
@router.post("/generate", response_model=FeedbackGenerationResponse)
async def generate_feedback(request: FeedbackGenerationRequest):
    try:
        logger.info(f"피드백 생성 시작")

        # 입력 데이터 유효성 검사
        if not request.feedbacks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="문제 데이터가 없습니다.",
            )

        # AI 에이전트를 통한 피드백 생성
        feedback_response = await test_feedback(
            exam_goal=request.test_summary,
            question_results=[q.model_dump(by_alias=True) for q in request.feedbacks],
        )

        logger.info(f"피드백 생성 완료")
        return feedback_response

    except ValueError as ve:
        logger.error(f"입력 데이터 검증 오류: {str(ve)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"입력 데이터 오류: {str(ve)}",
        )
    except Exception as e:
        logger.error(f"피드백 생성 실패 Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"피드백 생성 중 오류가 발생했습니다: {str(e)}",
        )
