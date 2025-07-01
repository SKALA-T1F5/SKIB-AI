# ai/api/websocket/services/progress_tracker.py
import json
import logging
from datetime import datetime
from typing import Optional

from api.websocket.schemas.task_progress import TaskProgress, TaskStatus
from db.redisDB.redis_client import redis_client

logger = logging.getLogger(__name__)


# Redis 키 생성기
def get_task_progress_key(task_id: str) -> str:
    """작업 진행률 Redis 키 생성"""
    return f"task_progress:{task_id}"


def get_retry_queue_key() -> str:
    """재시도 큐 Redis 키 생성"""
    return "task_retry_queue"


# 진행률 관리 함수들
async def save_task_progress(
    task_id: str, status: TaskStatus, progress: float, message: Optional[str] = None
) -> bool:
    """작업 진행률을 Redis에 저장"""
    try:
        now = datetime.now()

        # 기존 데이터 조회 (created_at 유지)
        existing = await get_task_progress(task_id)
        created_at = existing.created_at if existing else now

        task_progress = TaskProgress(
            task_id=task_id,
            status=status,
            progress=progress,
            message=message,
            created_at=created_at,
            updated_at=now,
        )

        key = get_task_progress_key(task_id)
        await redis_client.set(
            key, task_progress.model_dump_json(), ex=3600
        )  # 1시간 TTL

        logger.info(f"✅ 진행률 저장: {task_id} - {status.value} ({progress}%)")
        return True

    except Exception as e:
        logger.error(f"❌ 진행률 저장 실패 ({task_id}): {e}")
        return False


async def get_task_progress(task_id: str) -> Optional[TaskProgress]:
    """작업 진행률을 Redis에서 조회"""
    try:
        key = get_task_progress_key(task_id)
        raw_data = await redis_client.get(key)

        if raw_data:
            data = json.loads(raw_data)
            return TaskProgress(**data)

        return None

    except Exception as e:
        logger.error(f"❌ 진행률 조회 실패 ({task_id}): {e}")
        return None


async def update_task_progress(
    task_id: str, status: TaskStatus, progress: float, message: Optional[str] = None
) -> bool:
    """작업 진행률 업데이트 (저장과 동일)"""
    return await save_task_progress(task_id, status, progress, message)


async def cleanup_task_progress(task_id: str) -> bool:
    """작업 완료시 진행률 정리"""
    try:
        key = get_task_progress_key(task_id)
        await redis_client.delete(key)
        logger.info(f"🗑️ 진행률 정리 완료: {task_id}")
        return True

    except Exception as e:
        logger.error(f"❌ 진행률 정리 실패 ({task_id}): {e}")
        return False


# 재시도 큐 관리
async def add_to_retry_queue(
    task_id: str, status: TaskStatus, progress: float, message: Optional[str] = None
):
    """실패한 알림을 재시도 큐에 추가"""
    try:
        retry_data = {
            "task_id": task_id,
            "status": status.value,
            "progress": progress,
            "message": message,
            "retry_at": datetime.now().isoformat(),
        }

        key = get_retry_queue_key()
        await redis_client.lpush(key, json.dumps(retry_data))
        logger.warning(f"🔄 재시도 큐 추가: {task_id}")

    except Exception as e:
        logger.error(f"❌ 재시도 큐 추가 실패 ({task_id}): {e}")


async def get_retry_queue_items(limit: int = 10) -> list:
    """재시도 큐에서 항목들 조회"""
    try:
        key = get_retry_queue_key()
        items = await redis_client.lrange(key, 0, limit - 1)
        return [json.loads(item) for item in items]

    except Exception as e:
        logger.error(f"❌ 재시도 큐 조회 실패: {e}")
        return []


async def remove_from_retry_queue(retry_data: dict):
    """재시도 성공한 항목을 큐에서 제거"""
    try:
        key = get_retry_queue_key()
        await redis_client.lrem(key, 1, json.dumps(retry_data))

    except Exception as e:
        logger.error(f"❌ 재시도 큐 제거 실패: {e}")
