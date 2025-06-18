# agents/test_feedback/agent.py
import os
import openai
import json

from openai import AsyncOpenAI
from typing import List, Dict, Any
from api.grading.schemas.subjective_grading import GradingCriterion
from utils.parse_json_response import parse_json_response

from dotenv import load_dotenv
from src.agents.test_feedback.prompt import SYSTEM_PROMPT, build_user_prompt


#openai 로드
load_dotenv(override=True) 
api_key = os.getenv("OPENAI_API_KEY") 
openai_client = AsyncOpenAI(api_key=api_key) 
AGENT_MODEL = os.getenv("AGENT_TEST_FEEDBACK_MODEL") #.env에 모델명 저장 (AGENT_TEST_FEEDBACK_MODEL=gpt-4)✅

async def test_feedback(exam_goal: str, question_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    OpenAI를 이용하여 시험목표와 문항별 응시 결과를 분석하고 종합적인 피드백을 반환
    """
    # 1. 채점 기준을 문자열로 변환 (선택사항)
    # criteria_prompt = ""
    # if grading_criteria:
    #     criteria_prompt = "\n".join([
    #         f"{c.score} | {c.criteria} | ex: {c.example}" for c in grading_criteria
    #     ])

    # 2. 최종 프롬프트 구성
    USER_PROMPT = build_user_prompt(exam_goal, question_results)

    # 3. MODEL 호출
    try:
        # RAW INPUT 출력 #########################################
        print("\n" + "="*80)
        print("🤖 MODEL INPUT (RAW)")
        print("="*80)
        print("📋 SYSTEM PROMPT:")
        print(SYSTEM_PROMPT)
        print("\n📝 USER PROMPT:")
        print(USER_PROMPT)
        print("="*80)
        ########################################################
        
        response = await openai_client.chat.completions.create(
            model=AGENT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT}
            ],
            temperature=0.2,
        )

        content = response.choices[0].message.content.strip()
        
        # RAW OUTPUT 출력 #########################################
        print("\n" + "="*80)
        print("🤖 MODEL OUTPUT (RAW)")
        print("="*80)
        print(content)
        print("="*80)
        ########################################################

        result = json.loads(content)

        # 토큰 사용량 (차후 주석처리 ✅ )
        usage = response.usage
        print("🟨 사용 토큰:", usage.total_tokens)
        print("└─ prompt_tokens:", usage.prompt_tokens)
        print("└─ completion_tokens:", usage.completion_tokens)
        
        return result

    except Exception as e:
        raise RuntimeError(f"시험 피드백 생성 오류: {str(e)}")