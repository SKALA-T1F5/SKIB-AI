# agents/trainee_assistant/agent.py
import json
import os
import re
from typing import Any, Dict, List, Optional

import openai
from openai import AsyncOpenAI

from config.settings import settings
from src.agents.trainee_assistant.prompt import SYSTEM_PROMPT, build_user_prompt

# OpenAI 로드
api_key = settings.api_key
openai_client = AsyncOpenAI(api_key=api_key)
AGENT_MODEL = settings.subjective_grader_model


async def trainee_assistant_chat(
    user_question: str, question_info: dict, message_history: list
) -> str:
    """
    Trainee Assistant 챗봇 - 시험 문제 관련 질문에 답변
    user_question: str - 사용자의 질문
    question_info: dict - 문항 정보
    message_history: list - 이전 대화 내역
    """
    USER_PROMPT = build_user_prompt(user_question, question_info, message_history)

    try:
        # RAW INPUT 출력 #########################################
        print("\n" + "=" * 80)
        print("🤖 MODEL INPUT (RAW)")
        print("=" * 80)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ]
        print(messages)
        ########################################################

        response = await openai_client.chat.completions.create(
            model=AGENT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT},
            ],
            temperature=0.2,
            stream=False,
        )
        content = response.choices[0].message.content.strip()

        return content

    except Exception as e:
        raise RuntimeError(f"챗봇 오류: {str(e)}")


# FastAPI 라우터용 함수
async def get_chat_response(
    user_question: str, question_info: dict, message_history: list
) -> str:
    """
    FastAPI에서 사용할 챗봇 응답 함수
    """
    return await trainee_assistant_chat(user_question, question_info, message_history)
