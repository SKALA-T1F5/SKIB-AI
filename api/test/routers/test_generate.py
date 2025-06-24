from fastapi import APIRouter, HTTPException

from api.test.schemas.test_generate import (
    TestGenerationRequest,
    TestGenerationResponse,
)
from src.pipelines.test_generation.pipelines import TestGenerationPipeline

router = APIRouter(prefix="/api/test", tags=["Test"])


# 단순한 동기 Router (SpringBoot 연동 테스트용)
@router.post("/generate", response_model=TestGenerationResponse)
async def generate_test_questions(request: TestGenerationRequest):
    """
    단순 동기 처리 - SpringBoot 연동 테스트용
    """
    try:
        # Pipeline 직접 실행 (메모리 내)
        pipeline = TestGenerationPipeline()
        result = await pipeline.run(request)

        # 즉시 결과 반환 (TestGenerationResponse의 필드에 맞게 반환)
        return TestGenerationResponse(
            questions=result.get("questions", []),
            totalQuestions=result.get("totalQuestions", 0),
            objectiveCount=result.get("objectiveCount", 0),
            subjectiveCount=result.get("subjectiveCount", 0),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
