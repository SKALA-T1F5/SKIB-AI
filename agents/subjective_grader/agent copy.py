import os
import openai
from typing import List, Tuple
from api.grading.schemas.subjective_grading import GradingCriterion

from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv(override=True)

# 환경 변수에서 API 키 불러오기
api_key = os.getenv("OPENAI_API_KEY")

# OpenAI 클라이언트 생성
openai_client = openai.OpenAI(api_key=api_key)

async def subjective_grader(user_answer: str, grading_criteria: List[GradingCriterion]) -> Tuple[float, GradingCriterion]:
    """
    OpenAI를 이용하여 사용자 답변을 기준들과 비교하고 가장 적절한 기준을 선택해 점수를 반환
    """
    criteria_prompt = "\n\n".join([
        f"점수: {c.score}\n기준: {c.criteria}\n예시: {c.example}\n비고: {c.note}" for c in grading_criteria
    ])

    prompt = f"""
        당신은 채점 보조 AI입니다.

        다음은 사용자 답변입니다:
        "{user_answer}"

        아래는 채점 기준입니다:
        {criteria_prompt}

        사용자의 답변이 어떤 기준에 가장 부합하는지 판단하여 점수(score)와 선택된 기준(criteria 전체)를 JSON 형식으로 반환하세요.

        예시 출력:
        {{
        "score": 0.5,
        "selected_criteria": {{
            "score": 0.5,
            "criteria": "...",
            "example": "...",
            "note": "..."
        }}
        }}
    """

    # response = openai_client.chat.completions.create(
    #     model="gpt-4",
    #     messages=[
    #         {"role": "system", "content": "당신은 정직하고 논리적인 채점 AI입니다."},
    #         {"role": "user", "content": prompt}
    #     ],
    #     temperature=0.2
    # )

    # content = response['choices'][0]['message']['content']
    import json
    sample_response = {
        "score": 3,
        "selected_criteria": {
            "score": 3,
            "criteria": "예시 기준",
            "example": "예시 답변",
            "note": "예시 비고"
        }
    }

    return parse_response(sample_response)

# def parse_response(content: str) -> Tuple[float, GradingCriterion]:
def parse_response(data: dict) -> Tuple[float, GradingCriterion]:
    criteria = GradingCriterion(**data['selected_criteria'])
    return data['score'], criteria