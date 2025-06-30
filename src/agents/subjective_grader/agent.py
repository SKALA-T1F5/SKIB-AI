# agents/subjective_grader/agent.py
import json
from typing import List

from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI

from api.grading.schemas.subjective_grading import GradingCriterion
from config.settings import settings
from src.agents.subjective_grader.prompt import SYSTEM_PROMPT, build_user_prompt


def get_openai_client():
    api_key = settings.api_key
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")
    return wrap_openai(AsyncOpenAI(api_key=api_key))


def get_model_name():
    model = settings.subjective_grader_model
    if not model:
        raise ValueError("AGENT_SUBJECTIVE_GRADER_MODEL is not set.")
    return model


@traceable(
    run_type="chain",
    name="Subjective Grader",
    metadata={"agent_type": "subjective_grader"},  # 모델 이름은 동적으로 처리됨
)
async def subjective_grader(
    user_answer: str, grading_criteria: List[GradingCriterion]
) -> float:
    """
    사용자 답변을 기준들과 비교하고 점수(float)를 반환합니다.
    """
    # 1. 구성 요소 준비
    openai_client = get_openai_client()
    model_name = get_model_name()

    # 2. 채점 기준 문자열화
    criteria_prompt = "\n".join(
        [f"{c.score} | {c.criteria} | ex: {c.example}" for c in grading_criteria]
    )

    # 3. 프롬프트 구성
    prompt = build_user_prompt(user_answer, criteria_prompt)

    # 4. GPT 호출
    try:
        response = await openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )

        content = response.choices[0].message.content.strip()

        # 5. 결과 파싱 및 반환
        result = json.loads(content)
        return float(result["score"])

    except json.JSONDecodeError:
        raise RuntimeError(
            f"주관식 채점 오류: GPT 응답을 JSON으로 파싱할 수 없습니다.\n응답 내용: {content}"
        )
    except Exception as e:
        raise RuntimeError(f"주관식 채점 오류: {str(e)}")
