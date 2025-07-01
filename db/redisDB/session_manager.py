import json
from typing import List

from api.trainee_assistant.schemas.trainee_assistant import Question
from db.redisDB.redis_client import redis_client


# Redis 키 생성기
def get_test_questions_key(user_id: str) -> str:
    return f"test_questions:{user_id}"


def get_chat_history_key(user_id: str) -> str:
    return f"skib:user_session:{user_id}"


# 테스트 문항 저장
async def save_test_questions(user_id: str, questions: List[Question]):
    key = get_test_questions_key(user_id)
    await redis_client.set(key, json.dumps([q.dict() for q in questions]))


# 메시지 히스토리 저장
async def save_message_history(user_id: str, history: list):
    key = get_chat_history_key(user_id)
    await redis_client.set(key, json.dumps(history))


# 메시지 히스토리 로드
async def load_message_history(user_id: str) -> list:
    key = get_chat_history_key(user_id)
    raw = await redis_client.get(key)
    return json.loads(raw) if raw else []


# 테스트 문항 로드
async def load_test_questions(user_id: str) -> list[Question]:
    key = get_test_questions_key(user_id)
    raw = await redis_client.get(key)
    return [Question.parse_obj(q) for q in json.loads(raw)] if raw else []


# 히스토리에 메시지 추가
async def append_message(user_id: str, role: str, content: str):
    history = await load_message_history(user_id)
    history.append({"role": role, "content": content})
    await save_message_history(user_id, history)


# 세션 초기화
async def clear_user_session(user_id: str):
    """
    테스트 종료 시 Redis에 저장된 사용자 세션 정보 삭제
    """
    keys = [
        get_test_questions_key(user_id),
        get_chat_history_key(user_id),
    ]
    await redis_client.delete(*keys)


def get_test_progress_key(task_id: str) -> str:
    """테스트 진행률 Redis 키 생성"""
    return f"test_progress:{task_id}"


async def save_test_progress(task_id: str, progress_data: dict):
    """테스트 진행률 저장 (JSON 형태)"""
    key = get_test_progress_key(task_id)
    await redis_client.set(key, json.dumps(progress_data), ex=3600)  # 1시간 TTL


async def load_test_progress(task_id: str) -> Optional[dict]:
    """테스트 진행률 로드"""
    key = get_test_progress_key(task_id)
    raw = await redis_client.get(key)
    return json.loads(raw) if raw else None


async def clear_test_progress(task_id: str):
    """테스트 진행률 삭제"""
    key = get_test_progress_key(task_id)
    await redis_client.delete(key)
