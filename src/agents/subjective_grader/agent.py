# agents/subjective_grader/agent.py
import json
import os
from typing import List

from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI

from api.grading.schemas.subjective_grading import GradingCriterion
from config.settings import settings
from src.agents.subjective_grader.prompt import SYSTEM_PROMPT, build_user_prompt

# openai 로드
api_key = settings.api_key
openai_client = wrap_openai(AsyncOpenAI(api_key=api_key))
AGENT_MODEL = settings.subjective_grader_model

if AGENT_MODEL is None:
    raise ValueError("AGENT_SUBJECTIVE_GRADER_MODEL environment variable is not set.")


@traceable(
    run_type="chain",
    name="Subjective Grader",
    metadata={"agent_type": "subjective_grader", "model": AGENT_MODEL},
)
async def subjective_grader(
    user_answer: str, grading_criteria: List[GradingCriterion]
) -> float:
    """
    OpenAI를 이용하여 사용자 답변을 기준들과 비교하고 점수만 반환
    """
    # 채점 기준을 문자열로 변환
    # criteria_prompt = "\n\n".join([
    #     f"점수: {c.score}\n기준: {c.criteria}\n예시: {c.example}\n비고: {c.note}" for c in grading_criteria
    # ])

    # 1. 채점 기준을 문자열로 변환
    criteria_prompt = "\n".join(
        [f"{c.score} | {c.criteria} | ex: {c.example}" for c in grading_criteria]
    )

    # 2. 최종 프롬프트 구성
    prompt = build_user_prompt(user_answer, criteria_prompt)

    # 3. MODEL 호출
    try:
        response = await openai_client.chat.completions.create(
            model=AGENT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        content = response.choices[0].message.content.strip()
        result = json.loads(content)

        # 토큰 사용량 (차후 주석처리 ✅ )
        response.usage

        return float(result["score"])

    except Exception as e:
        raise RuntimeError(f"주관식 채점 오류: {str(e)}")
