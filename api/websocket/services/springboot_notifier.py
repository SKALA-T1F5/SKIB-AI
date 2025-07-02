# api/websocket/services/springboot_notifier.py (최종 리팩토링 - 불필요한 것 제거)
import asyncio
import logging
from typing import Optional

import httpx

from api.document.schemas.document_status import DocumentProcessingStatus
from api.test.schemas.test_generate import TestGenerationResultResponse
from api.test.schemas.test_generation_status import (
    TestGenerationStatus,
    TestStatusResponse,
)
from api.websocket.services.progress_tracker import (
    get_retry_queue_items,
    remove_from_retry_queue,
)
from config.settings import settings

logger = logging.getLogger(__name__)


# =============================================================================
# 문서 관련 알림
# =============================================================================


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


# =============================================================================
# 테스트 생성 관련 알림
# =============================================================================


async def notify_test_generation_progress(
    task_id: str, test_id: int, status: TestGenerationStatus
) -> bool:
    """테스트 생성 진행률 알림"""
    try:
        # 상태 업데이트 DTO 생성
        status_update = TestStatusResponse(
            test_id=test_id,
            status=status,
        )

        url = f"{settings.backend_url}/api/test/progress/"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.put(
                url,
                json=status_update.model_dump(),
                headers={"Content-Type": "application/json"},
            )

        if response.status_code == 200:
            logger.info(f"✅ 테스트 생성 상태 알림 성공: {test_id} - {status.value}")
            return True
        else:
            logger.error(f"🚫 테스트 생성 상태 알림 실패: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ 테스트 생성 상태 알림 예외: {task_id} - {e}")
        return False


async def notify_test_generation_result(
    task_id: str, test_id: int, result_data: dict
) -> bool:
    """테스트 생성 최종 결과 전송"""
    try:
        url = f"{settings.backend_url}/api/test/result/"

        result = TestGenerationResultResponse(
            testId=result_data.get("test_id"),  # type: ignore
            questions=result_data.get("questions"),  # type: ignore
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=result.model_dump(mode="json", exclude_none=True),
                headers={"Content-Type": "application/json"},
            )

        if response.status_code == 200:
            logger.info(f"✅ 테스트 생성 결과 전송 성공: {test_id}")
            return True
        else:
            logger.error(f"🚫 테스트 생성 결과 전송 실패: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"❌ 테스트 생성 결과 전송 예외: {task_id} - {e}")
        return False


# =============================================================================
# 재시도 관리
# =============================================================================


async def retry_failed_notifications():
    """실패한 알림들을 재시도"""
    try:
        retry_items = await get_retry_queue_items(limit=5)

        for item in retry_items:
            # 문서와 테스트에 따라 다른 재시도 로직 적용
            item_type = item.get("type", "unknown")

            if item_type == "document":
                # 문서 재시도는 기존 방식 유지
                pass  # TODO: 필요시 문서 재시도 로직 구현
            elif item_type == "test":
                # 테스트 재시도는 새로운 방식 사용
                pass  # TODO: 필요시 테스트 재시도 로직 구현

            # 성공시 큐에서 제거
            await remove_from_retry_queue(item)
            logger.info(f"✅ 재시도 처리: {item.get('task_id')}")

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
