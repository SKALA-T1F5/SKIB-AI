import json

from db.redisDB.redis_client import redis_client


def get_session_key(user_id: str) -> str:
    return f"skib:user_session:{user_id}"


async def save_message_history(user_id: str, history: list):
    key = get_session_key(user_id)
    await redis_client.set(key, json.dumps(history))


async def load_message_history(user_id: str) -> list:
    key = get_session_key(user_id)
    raw = await redis_client.get(key)
    return json.loads(raw) if raw else []


async def append_message(user_id: str, role: str, content: str):
    history = await load_message_history(user_id)
    history.append({"role": role, "content": content})
    await save_message_history(user_id, history)
