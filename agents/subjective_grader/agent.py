# agents/subjective_grader/agent.py
import os
import openai
import json

from openai import AsyncOpenAI
from typing import List
from api.grading.schemas.subjective_grading import GradingCriterion

from dotenv import load_dotenv
from agents.subjective_grader.prompt import SYSTEM_PROMPT, build_user_prompt


#openai 로드
load_dotenv(override=True) 
api_key = os.getenv("OPENAI_API_KEY") 
openai_client = AsyncOpenAI(api_key=api_key) 
AGENT_MODEL = os.getenv("AGENT_SUBJECTIVE_GRADER_MODEL") #차후 .env에 모델명 저장 (AGENT_SUBJECTIVE_GRADER_MODEL=gpt-4)✅

async def subjective_grader(user_answer: str, grading_criteria: List[GradingCriterion]) -> float:
    """
    OpenAI를 이용하여 사용자 답변을 기준들과 비교하고 점수만 반환
    """
    # 채점 기준을 문자열로 변환 1
    # criteria_prompt = "\n\n".join([
    #     f"점수: {c.score}\n기준: {c.criteria}\n예시: {c.example}\n비고: {c.note}" for c in grading_criteria
    # ])
    # 채점 기준을 문자열로 변환 2
    criteria_prompt = "\n".join([
    f"{c.score} | {c.criteria} | ex: {c.example}" for c in grading_criteria
])


    # 사용자에게 줄 최종 프롬프트 구성
    prompt = build_user_prompt(user_answer, criteria_prompt)

    # MODEL 호출
    try:
        response = await openai_client.chat.completions.create(
            model=AGENT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
        )

        content = response.choices[0].message.content.strip()
        result = json.loads(content)

        # 토큰 사용량 (차후 주석처리 ✅ )
        usage = response.usage
        print("🟨 사용 토큰:", usage.total_tokens)
        print("└─ prompt_tokens:", usage.prompt_tokens)
        print("└─ completion_tokens:", usage.completion_tokens)
        
        return float(result["score"]) 

    except Exception as e:
        raise RuntimeError(f"OpenAI 채점 오류: {str(e)}")