# agents/trainee_assistant/agent.py
import os
import openai
import json
import re

from openai import AsyncOpenAI
from src.agents.trainee_assistant.prompt import SYSTEM_PROMPT, build_user_prompt
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# OpenAI 로드
load_dotenv(override=True) 
api_key = os.getenv("OPENAI_API_KEY") 
openai_client = AsyncOpenAI(api_key=api_key) 
AGENT_MODEL = os.getenv("AGENT_TEST_FEEDBACK_MODEL") #.env에 모델명 저장 (AGENT_TEST_FEEDBACK_MODEL=gpt-4)✅



async def trainee_assistant_chat(user_question: str, question_info: dict, message_history: list) -> str:
    """
    Trainee Assistant 챗봇 - 시험 문제 관련 질문에 답변
    user_question: str - 사용자의 질문
    question_info: dict - 문항 정보
    message_history: list - 이전 대화 내역
    """
    USER_PROMPT = build_user_prompt(user_question, question_info, message_history)

    try:
        # RAW INPUT 출력 #########################################
        print("\n" + "="*80)
        print("🤖 MODEL INPUT (RAW)")
        print("="*80)
        messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT}
            ]
        print(messages)
        ########################################################

        response = await openai_client.chat.completions.create(
            model=AGENT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT}
            ],
            temperature=0.2,
            stream=False,
        )
        content = response.choices[0].message.content.strip()         
        
        return content

    except Exception as e:
        raise RuntimeError(f"챗봇 오류: {str(e)}")

# FastAPI 라우터용 함수
async def get_chat_response(user_question: str, question_info: dict, message_history: list) -> str:
    """
    FastAPI에서 사용할 챗봇 응답 함수
    """
    return await trainee_assistant_chat(user_question, question_info, message_history)
