"""
Test Generation Pipeline용 Celery Task - Question Generation
- Redis에서 컨텍스트 로드
- QuestionGeneratorAgent로 문제 생성
- Redis에 문제 저장
- LangGraph State용 품질 점수 반환
"""

import logging
from typing import Any, Dict

from config.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 2, "countdown": 30},
    name="test_generation.question_generation",
)
def question_generation_task(
    self,
    pipeline_id: str,
    batch_id: int,
    target_questions: Dict[str, int],  # {"objective": 3, "subjective": 2}
    document_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    컨텍스트 기반 문제 생성 Celery Task

    Args:
        pipeline_id: Pipeline 고유 ID
        batch_id: 배치 ID
        target_questions: 생성할 문제 수
        document_metadata: 문서 메타데이터

    Returns:
        Dict: 문제 생성 결과 및 품질 점수
    """
    task_id = self.request.id
    logger.info(f"🤖 Question Generation 시작: Task {task_id}, Batch {batch_id}")

    try:
        # 1. Redis에서 컨텍스트 로드
        import asyncio

        from db.redisDB.testgen_session_manager import load_batch_contexts

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            contexts = loop.run_until_complete(
                load_batch_contexts(pipeline_id, batch_id)
            )
        finally:
            loop.close()

        if not contexts:
            raise Exception(f"배치 {batch_id}의 컨텍스트를 찾을 수 없습니다")

        logger.info(f"📋 컨텍스트 로드 완료: {len(contexts)}개")

        # 2. 문제 생성
        from src.agents.question_generator.agent import generate_questions_for_batch

        result = generate_questions_for_batch(
            contexts=contexts,
            target_questions=target_questions,
            document_metadata=document_metadata,
        )

        if result["status"] != "success":
            raise Exception(f"문제 생성 실패: {result.get('error', 'Unknown error')}")

        questions = result["questions"]
        quality_score = result["metadata"]["quality_score"]

        # 3. Redis에 생성된 문제 저장
        from db.redisDB.testgen_session_manager import save_batch_questions

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            questions_saved = loop.run_until_complete(
                save_batch_questions(pipeline_id, batch_id, questions)
            )
        finally:
            loop.close()

        if not questions_saved:
            logger.warning(
                f"⚠️ 문제 Redis 저장 실패 (Pipeline: {pipeline_id}, Batch: {batch_id})"
            )

        # 4. 배치 요약 저장 (LangGraph 조건부 분기용)
        from db.redisDB.testgen_session_manager import save_batch_summary

        batch_summary = {
            "batch_id": batch_id,
            "status": "completed",
            "questions_generated": len(questions),
            "average_quality": quality_score,
            "target_objective": target_questions.get("objective", 0),
            "target_subjective": target_questions.get("subjective", 0),
            "actual_objective": result["metadata"]["objective_count"],
            "actual_subjective": result["metadata"]["subjective_count"],
            "processing_time": getattr(self.request, "processing_time", None),
            "contexts_used": len(contexts),
        }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(
                save_batch_summary(pipeline_id, batch_id, batch_summary)
            )
        finally:
            loop.close()

        # 5. 성공 결과 반환
        logger.info(
            f"✅ Question Generation 완료: {len(questions)}개 문제, 품질: {quality_score:.3f}"
        )

        return {
            "status": "success",
            "pipeline_id": pipeline_id,
            "batch_id": batch_id,
            "questions_generated": len(questions),
            "quality_score": quality_score,
            "target_questions": target_questions,
            "actual_questions": {
                "objective": result["metadata"]["objective_count"],
                "subjective": result["metadata"]["subjective_count"],
            },
            "task_id": task_id,
        }

    except Exception as e:
        logger.error(f"❌ Question Generation 실패 (Batch {batch_id}): {e}")

        # 재시도 로직
        if self.request.retries < 2:
            logger.info(f"🔄 재시도 예약 ({self.request.retries + 1}/2)")
            raise self.retry(countdown=30 * (self.request.retries + 1))

        # 최종 실패
        return {
            "status": "failed",
            "pipeline_id": pipeline_id,
            "batch_id": batch_id,
            "questions_generated": 0,
            "quality_score": 0.0,
            "error": str(e),
            "task_id": task_id,
        }


@celery_app.task(bind=True, name="test_generation.regenerate_questions")
def regenerate_questions_task(
    self,
    pipeline_id: str,
    batch_id: int,
    failed_questions_info: Dict[str, Any],
    retry_strategy: str = "different_approach",
) -> Dict[str, Any]:
    """
    실패한 문제 재생성 Task

    Args:
        pipeline_id: Pipeline 고유 ID
        batch_id: 배치 ID
        failed_questions_info: 실패한 문제 정보
        retry_strategy: 재시도 전략

    Returns:
        Dict: 재생성 결과
    """
    task_id = self.request.id
    logger.info(f"🔄 Question Regeneration 시작: Task {task_id}, Batch {batch_id}")

    try:
        # 실패 원인 분석
        failed_questions_info.get("reason", "low_quality")
        target_questions = failed_questions_info.get("target_questions", {})

        # 다른 전략 적용
        if retry_strategy == "different_approach":
            # 더 관대한 품질 기준 적용하거나 다른 컨텍스트 사용
            target_questions = {
                "objective": max(target_questions.get("objective", 0) - 1, 1),
                "subjective": max(target_questions.get("subjective", 0) - 1, 1),
            }

        # 기본 문제 생성 Task 재호출
        return question_generation_task(
            pipeline_id=pipeline_id,
            batch_id=batch_id,
            target_questions=target_questions,
            document_metadata=failed_questions_info.get("document_metadata", {}),
        )

    except Exception as e:
        logger.error(f"❌ Question Regeneration 실패: {e}")
        return {
            "status": "failed",
            "pipeline_id": pipeline_id,
            "batch_id": batch_id,
            "error": str(e),
            "task_id": task_id,
        }
