import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from api.test.schemas.test_generate import (
    TestGenerationRequest,
    TestGenerationResponse,
)
from api.test.schemas.test_generation_status import TestGenerationStatus
from api.websocket.services.springboot_notifier import notify_test_generation_progress
from config.tasks import generate_test_task

router = APIRouter(prefix="/api/test", tags=["Test"])
logger = logging.getLogger(__name__)


@router.post(
    "/generate",
    response_model=TestGenerationResponse,
    response_model_by_alias=True,
    response_model_exclude_none=False,
)
async def generate_test_questions(request: TestGenerationRequest):
    """
    비동기 테스트 생성 - 즉시 task_id 반환, 백그라운드에서 처리
    """
    try:
        # Task ID와 Test ID 생성
        task_id = str(uuid4())

        logger.info(f"테스트 생성 요청: test_id={request.test_id}, task_id={task_id}")

        # 초기 상태 알림
        await notify_test_generation_progress(
            task_id=task_id,
            test_id=request.test_id,
            status=TestGenerationStatus.TEST_GENERATION_STARTED,
        )

        # 요청 데이터를 dictionary로 변환
        request_data = {
            "test_id": request.test_id,
            "name": request.name,
            "summary": request.summary,
            "difficulty_level": request.difficulty_level.value,
            "limited_time": request.limited_time,
            "pass_score": request.pass_score,
            "is_retake": request.is_retake,
            "document_configs": [
                {
                    "documentId": doc.documentId,
                    "document_name": doc.document_name,
                    "keywords": doc.keywords,
                    "configured_objective_count": doc.configured_objective_count,
                    "configured_subjective_count": doc.configured_subjective_count,
                }
                for doc in request.document_configs
            ],
        }

        # Celery 백그라운드 작업 실행
        generate_test_task.delay(  # type: ignore
            task_id=task_id, test_id=request_data["test_id"], request_data=request_data
        )

        return TestGenerationResponse(
            testId=request_data["test_id"],
            message="테스트 생성이 시작되었습니다. 진행률을 확인하세요.",
        )

    except Exception as e:
        logger.error(f"❌ 테스트 생성 요청 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"테스트 생성 요청 실패: {str(e)}")
