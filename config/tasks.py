import asyncio
import logging
from typing import Any, Dict

from api.document.services.document_summary import process_document_background
from api.test.schemas.test_generation_status import TestGenerationStatus
from api.test.services.test_generate import test_generation_background
from api.websocket.services.springboot_notifier import notify_test_generation_progress
from config.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="process_document", queue="preprocessing_queue")
def process_document_task(
    task_id: str, file_path: str, documentId: int, project_id: int, filename: str
) -> Dict[str, Any]:
    """문서 처리 Celery Task"""
    try:
        logger.info(f"문서 처리 시작: task_id={task_id}, documentId={documentId}")

        # 내부 비동기 실행을 따로 함수로 분리
        result = run_async_process_document(
            task_id, file_path, documentId, project_id, filename
        )

        logger.info(f"문서 처리 완료: task_id={task_id}, documentId={documentId}")
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"[ERROR] 문서 처리 실패: {e}")
        return {"status": "failed", "error": str(e)}


def run_async_process_document(
    task_id: str, file_path: str, documentId: int, project_id: int, filename: str
) -> Dict[str, Any]:
    """동기 context에서 비동기 함수 실행 (event loop 안전 처리)"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # 이미 event loop가 실행 중이면 → 별도 Task로 실행
        coro = process_document_background(
            task_id, file_path, documentId, project_id, filename
        )
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()
    else:
        # 아니면 그냥 run
        return loop.run_until_complete(
            process_document_background(
                task_id, file_path, documentId, project_id, filename
            )
        )


@celery_app.task(name="generate_test", queue="generation_queue")
def generate_test_task(
    task_id: str, test_id: int, request_data: Dict[str, Any]
) -> Dict[str, Any]:
    """테스트 생성 Celery Task"""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        logger.info(f"테스트 문제 생성 시작: task_id={task_id}, test_id={test_id}")

        # 초기 상태 알림
        loop.run_until_complete(
            notify_test_generation_progress(
                task_id=task_id,
                test_id=test_id,
                status=TestGenerationStatus.TEST_GENERATION_STARTED,
            )
        )

        result = loop.run_until_complete(
            test_generation_background(task_id, test_id, request_data)
        )
        return {"status": "completed", "result": result}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
    finally:
        loop.close()
