# api/test/routers/test_generation.py (올바른 비동기 구현)
import asyncio
import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from api.question.schemas.question import (
    DifficultyLevel,
    GenerationType,
    GradingCriterion,
    QuestionResponse,
    QuestionType,
)
from api.test.schemas.test_generate import (
    TestGenerationRequest,
    TestGenerationResponse,
)
from api.test.schemas.test_status import TestStatus
from api.websocket.schemas.task_progress import TaskStatus
from api.websocket.services.progress_tracker import get_task_progress
from api.websocket.services.springboot_notifier import notify_test_progress
from src.agents.question_generator.agent import QuestionGeneratorAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/test", tags=["Test"])


# === 테스트 생성 관리 함수들 ===

# 단계별 진행률 매핑
STAGE_PROGRESS_MAP = {
    TestStatus.INITIALIZING: 5.0,
    TestStatus.PARSING_DOCUMENTS: 25.0,
    TestStatus.DESIGNING_TEST: 45.0,
    TestStatus.GENERATING_QUESTIONS: 80.0,
    TestStatus.FINALIZING: 100.0,
}


async def notify_test_stage(
    task_id: str,
    stage: TestStatus,
    custom_progress: Optional[float] = None,
    message: Optional[str] = None,
) -> bool:
    """테스트 생성 단계별 진행률 알림"""

    # 진행률 계산
    progress = (
        custom_progress if custom_progress is not None else STAGE_PROGRESS_MAP[stage]
    )

    # 상태 결정
    if progress >= 100.0:
        status = TaskStatus.COMPLETED
    elif progress > 0:
        status = TaskStatus.PROCESSING
    else:
        status = TaskStatus.PENDING

    # 메시지 생성
    if not message:
        message = _get_stage_message(stage)

    logger.info(f"📊 테스트 진행률 업데이트: {task_id} - {stage.value} ({progress}%)")

    return await notify_test_progress(task_id, status, progress, message)


def _get_stage_message(stage: TestStatus) -> str:
    """단계별 기본 메시지 생성"""
    messages = {
        TestStatus.INITIALIZING: "테스트 생성을 시작합니다",
        TestStatus.PARSING_DOCUMENTS: "문서를 분석하고 있습니다",
        TestStatus.DESIGNING_TEST: "테스트 구조를 설계하고 있습니다",
        TestStatus.GENERATING_QUESTIONS: "문제를 생성하고 있습니다",
        TestStatus.FINALIZING: "테스트 생성이 완료되었습니다",
    }
    return messages.get(stage, "처리 중입니다")


async def notify_test_error(task_id: str, error_message: str) -> bool:
    """테스트 생성 실패 알림"""
    logger.error(f"❌ 테스트 생성 실패: {task_id} - {error_message}")

    return await notify_test_progress(
        task_id, TaskStatus.FAILED, 0.0, f"오류 발생: {error_message}"
    )


# === 새로운 비동기 API (메인) ===


@router.post("/generate")
async def generate_test_async(request: TestGenerationRequest):
    """
    비동기 테스트 생성 - 즉시 task_id 반환, 백그라운드에서 처리
    """
    try:
        # Task ID 생성
        task_id = str(uuid4())

        # 초기 상태 알림
        await notify_test_stage(task_id, TestStatus.INITIALIZING)

        # 백그라운드에서 실제 테스트 생성 실행
        asyncio.create_task(background_test_generation(task_id, request))

        # 즉시 task_id 반환 (사용자는 1초 내 응답 받음)
        return {
            "task_id": task_id,
            "status": "PENDING",
            "message": "테스트 생성이 시작되었습니다. 진행 상황을 확인하세요.",
        }

    except Exception as e:
        logger.error(f"❌ 비동기 테스트 생성 시작 실패: {e}")
        raise HTTPException(status_code=500, detail="테스트 생성 시작 실패")


async def background_test_generation(task_id: str, request: TestGenerationRequest):
    """백그라운드에서 실제 테스트 생성 수행 (5분 소요)"""
    try:
        # 1. Agent 초기화
        await notify_test_stage(
            task_id, TestStatus.PARSING_DOCUMENTS, 15.0, "Agent 초기화 중"
        )
        agent = QuestionGeneratorAgent()

        # 2. 데이터 변환
        await notify_test_stage(
            task_id, TestStatus.DESIGNING_TEST, 35.0, "테스트 설계 중"
        )

        document_plans = []
        for doc_config in request.document_configs:
            document_plan = {
                "document_name": doc_config.document_name,
                "document_id": doc_config.documentId,
                "keywords": doc_config.keywords,
                "recommended_questions": {
                    "objective": doc_config.configured_objective_count,
                    "subjective": doc_config.configured_subjective_count,
                },
            }
            document_plans.append(document_plan)

        total_test_plan_data = {
            "test_summary": request.summary,
            "difficulty": request.difficulty_level.value.lower(),
            "total_objective": sum(
                doc.configured_objective_count for doc in request.document_configs
            ),
            "total_subjective": sum(
                doc.configured_subjective_count for doc in request.document_configs
            ),
        }

        document_test_plan_data = {"document_plans": document_plans}

        # 3. 실제 문제 생성 (가장 오래 걸리는 부분)
        await notify_test_stage(
            task_id, TestStatus.GENERATING_QUESTIONS, 60.0, "문제 생성 중..."
        )

        result = agent.generate_enhanced_questions_from_test_plans(
            total_test_plan_data=total_test_plan_data,
            document_test_plan_data=document_test_plan_data,
        )

        if result.get("status") == "failed":
            await notify_test_error(task_id, result.get("error", "문제 생성 실패"))
            return

        # 4. 결과 변환
        await notify_test_stage(task_id, TestStatus.FINALIZING, 90.0, "결과 변환 중")

        questions = []
        generated_questions = result.get("questions", [])

        for q in generated_questions:
            question_type = QuestionType(q.get("type"))

            difficulty_map = {
                "easy": DifficultyLevel.easy,
                "medium": DifficultyLevel.normal,
                "hard": DifficultyLevel.hard,
            }
            difficulty = difficulty_map.get(
                q.get("difficulty", "medium"), DifficultyLevel.normal
            )

            valid_criteria_fields = {"score", "criteria", "example", "note"}
            raw_criteria = q.get("grading_criteria", [])

            grading_criteria = [
                GradingCriterion(
                    **{k: v for k, v in criterion.items() if k in valid_criteria_fields}
                )
                for criterion in raw_criteria
                if isinstance(criterion, dict)
            ]

            question_response = QuestionResponse(
                type=question_type,
                generationType=GenerationType(q.get("generation_type").upper()),
                difficulty_level=difficulty,
                question=q.get("question", ""),
                options=(
                    q.get("options")
                    if question_type == QuestionType.objective
                    else None
                ),
                answer=q.get("answer", ""),
                explanation=q.get("explanation"),
                grading_criteria=(
                    grading_criteria
                    if question_type == QuestionType.subjective
                    else None
                ),
                documentId=q.get("document_id", 0),
                document_name=q.get("document_name", ""),
                keywords=q.get("source_keywords", []),
                tags=q.get("tags", []),
            )
            questions.append(question_response)

        # 5. 결과 저장 (Redis에 저장)
        from api.websocket.services.progress_tracker import save_task_progress
        from db.redisDB.session_manager import save_test_result

        result_data = TestGenerationResponse(questions=questions)

        # 결과 데이터를 Redis에 저장
        await save_test_result(task_id, result_data.model_dump())

        # 진행률 완료 상태로 업데이트
        await save_task_progress(
            task_id, TaskStatus.COMPLETED, 100.0, "테스트 생성 완료"
        )

        # 완료 알림
        await notify_test_stage(
            task_id, TestStatus.FINALIZING, 100.0, "테스트 생성 완료"
        )

        logger.info(f"✅ 테스트 생성 완료: {task_id}")

    except Exception as e:
        await notify_test_error(task_id, str(e))
        logger.error(f"❌ 백그라운드 테스트 생성 실패: {task_id} - {e}")


# === 진행률 및 결과 조회 API ===


@router.get("/generate/progress/{task_id}")
async def get_test_generation_progress(task_id: str):
    """테스트 생성 진행률 조회"""
    try:
        progress_data = await get_task_progress(task_id)

        if not progress_data:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        return {
            "task_id": progress_data.task_id,
            "status": progress_data.status.value,
            "progress": progress_data.progress,
            "message": progress_data.message,
            "updated_at": progress_data.updated_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 진행률 조회 실패 ({task_id}): {e}")
        raise HTTPException(status_code=500, detail="Progress retrieval failed")


@router.get("/generate/result/{task_id}", response_model=TestGenerationResponse)
async def get_test_generation_result(task_id: str):
    """테스트 생성 결과 조회 (완료 후)"""
    try:
        progress_data = await get_task_progress(task_id)

        if not progress_data:
            raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

        if progress_data.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Task not completed yet. Current status: {progress_data.status.value}",
            )

        # Redis에서 실제 결과 데이터 조회
        from db.redisDB.session_manager import load_test_result

        result_data = await load_test_result(task_id)

        if not result_data:
            raise HTTPException(status_code=404, detail="Result data not found")

        return TestGenerationResponse(**result_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 결과 조회 실패 ({task_id}): {e}")
        raise HTTPException(status_code=500, detail="Result retrieval failed")
