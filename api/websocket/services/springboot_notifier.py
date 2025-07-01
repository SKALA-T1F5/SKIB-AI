# ai/api/websocket/services/springboot_notifier.py
import asyncio
import logging
from typing import Optional

import httpx

from api.document.schemas.document_status import DocumentProcessingStatus
from api.test.schemas.test_status import TestStatus
from api.websocket.schemas.task_progress import ProgressUpdateRequest, TaskStatus
from api.websocket.services.progress_tracker import (
    add_to_retry_queue,
    get_retry_queue_items,
    remove_from_retry_queue,
    save_task_progress,
)
from config.settings import settings

logger = logging.getLogger(__name__)


# 엔드포인트 설정 (중앙 관리)
ENDPOINTS = {
    "test": "/api/task/progress",  # PUT 방식으로 변경
    "document": "/api/document/progress",
}


async def notify_progress_safe(
    task_id: str,
    status: TaskStatus,
    progress: float,
    message: Optional[str] = None,
    endpoint_type: str = "test",
) -> bool:
    """
    안전한 진행률 알림 - 실패해도 계속 진행
    1. Redis에 먼저 저장 (보장)
    2. SpringBoot 알림 시도 (실패 허용)

    Args:
        endpoint_type: "test" 또는 "document"
    """
    # 1. Redis에 먼저 저장 (필수)
    await save_task_progress(task_id, status, progress, message)

    # 2. SpringBoot 알림 시도 (실패 허용)
    success = await _notify_springboot(
        task_id, status, progress, message, endpoint_type
    )

    if not success:
        # 실패시 재시도 큐에 추가
        await add_to_retry_queue(task_id, status, progress, message)
        logger.warning(f"⚠️ SpringBoot 알림 실패, 재시도 큐 추가: {task_id}")

    return success


async def _notify_springboot(
    task_id: str,
    status: TaskStatus,
    progress: float,
    message: Optional[str] = None,
    endpoint_type: str = "test",
) -> bool:
    """SpringBoot에 진행률 알림 전송"""
    try:
        # DTO 생성
        progress_update = ProgressUpdateRequest(
            status=status, progress=progress, message=message
        )

        # URL 구성
        endpoint = ENDPOINTS.get(endpoint_type, ENDPOINTS["test"])
        url = f"{settings.backend_url}{endpoint}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json=progress_update.model_dump(),
                headers={"Content-Type": "application/json"},
            )

        if response.status_code == 200:
            logger.info(
                f"✅ SpringBoot 알림 성공: {task_id} - {status.value} ({progress}%)"
            )
            return True
        else:
            logger.error(
                f"🚫 SpringBoot 알림 실패: {response.status_code} - {response.text}"
            )
            return False

    except asyncio.TimeoutError:
        logger.error(f"⏰ SpringBoot 알림 타임아웃: {task_id}")
        return False
    except Exception as e:
        logger.error(f"❌ SpringBoot 알림 예외: {task_id} - {e}")
        return False


async def _notify_springboot_test_status(
    task_id: str,
    document_id: int,
    status: "TestStatus",
    error_code: Optional[str] = None,
) -> bool:
    """SpringBoot에 테스트 상태 알림 (PUT 방식)"""
    try:
        from api.test.schemas.test_status import TestStatusResponse

        # 상태 업데이트 DTO 생성
        status_update = TestStatusResponse(
            documentId=document_id,
            status=status,
        )

        url = f"{settings.backend_url}/api/test/progress"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(
                url,
                json=status_update.model_dump(),
                headers={"Content-Type": "application/json"},
            )

        if response.status_code == 200:
            logger.info(f"✅ SpringBoot 상태 알림 성공: {task_id} - {status.value}")

            return True
        else:
            logger.error(f"🚫 SpringBoot 상태 알림 실패: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ SpringBoot 상태 알림 예외: {task_id} - {e}")
        return False


async def _notify_springboot_document_status(
    task_id: str,
    document_id: int,
    status: DocumentProcessingStatus,
    error_code: Optional[str] = None,
) -> bool:
    """SpringBoot에 문서 상태 알림 (PUT 방식)"""
    try:
        from api.document.schemas.document_status import DocumentStatusUpdateDto

        # 상태 업데이트 DTO 생성
        status_update = DocumentStatusUpdateDto(
            documentId=document_id,
            status=status,
        )

        url = f"{settings.backend_url}/api/document/progress"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(
                url,
                json=status_update.model_dump(),
                headers={"Content-Type": "application/json"},
            )

        if response.status_code == 200:
            logger.info(
                f"✅ SpringBoot 문서 상태 알림 성공: {task_id} - {status.value}"
            )

            # SpringBoot 응답 파싱
            try:
                from api.document.schemas.document_status import (
                    SpringBootDocumentResponse,
                )

                response_data = SpringBootDocumentResponse(**response.json())
                logger.info(f"📡 SpringBoot 응답: {response_data.code}")
            except Exception as e:
                logger.warning(f"⚠️ SpringBoot 응답 파싱 실패: {e}")

            return True
        else:
            logger.error(f"🚫 SpringBoot 문서 상태 알림 실패: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ SpringBoot 문서 상태 알림 예외: {task_id} - {e}")
        return False


def _map_progress_to_stage(progress: float):
    """진행률을 기반으로 TestStatus 매핑"""
    from api.test.schemas.test_status import TestStatus

    if progress < 10:
        return TestStatus.INITIALIZING
    elif progress < 30:
        return TestStatus.PARSING_DOCUMENTS
    elif progress < 50:
        return TestStatus.DESIGNING_TEST
    elif progress < 90:
        return TestStatus.GENERATING_QUESTIONS
    else:
        return TestStatus.FINALIZING


# 도메인별 편의 함수들
async def notify_test_progress(
    task_id: str, status: TaskStatus, progress: float, message: Optional[str] = None
) -> bool:
    """테스트 진행률 알림 (단순화된 버전)"""

    # progress를 기반으로 TestStatus 결정
    test_stage = _map_progress_to_stage(progress)

    # documentId는 임시로 1, 실제로는 request에서 전달받아야 함
    return await _notify_springboot_test_status(
        task_id=task_id,
        document_id=1,  # TODO: 실제 document_id 전달
        status=test_stage,
        error_code=None if status != TaskStatus.FAILED else "GENERATION_FAILED",
    )


async def notify_document_progress(
    task_id: str,
    document_id: int,
    status: DocumentProcessingStatus,
    error_code: Optional[str] = None,
) -> bool:
    """문서 처리 진행률 알림"""
    return await _notify_springboot_document_status(
        task_id=task_id, document_id=document_id, status=status, error_code=error_code
    )


# 재시도 관리
async def retry_failed_notifications():
    """실패한 알림들을 재시도"""
    try:
        retry_items = await get_retry_queue_items(limit=5)

        for item in retry_items:
            success = await _notify_springboot(
                task_id=item["task_id"],
                status=TaskStatus(item["status"]),
                progress=item["progress"],
                message=item.get("message"),
                endpoint_type="test",  # 기본값
            )

            if success:
                await remove_from_retry_queue(item)
                logger.info(f"✅ 재시도 성공: {item['task_id']}")
            else:
                logger.warning(f"🔄 재시도 실패: {item['task_id']}")

    except Exception as e:
        logger.error(f"❌ 재시도 작업 중 예외: {e}")


# 백그라운드 재시도 워커
_retry_worker_running = False


async def start_retry_worker():
    """백그라운드 재시도 워커 시작"""
    global _retry_worker_running

    if _retry_worker_running:
        return

    _retry_worker_running = True
    logger.info("🚀 재시도 워커 시작")

    while _retry_worker_running:
        try:
            await retry_failed_notifications()
            await asyncio.sleep(60)  # 1분마다 재시도
        except Exception as e:
            logger.error(f"❌ 재시도 워커 예외: {e}")
            await asyncio.sleep(60)


def stop_retry_worker():
    """백그라운드 재시도 워커 중지"""
    global _retry_worker_running
    _retry_worker_running = False
    logger.info("🛑 재시도 워커 중지")
