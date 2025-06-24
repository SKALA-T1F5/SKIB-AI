# agents/test_feedback/agent.py
import os
import openai
from google import genai
import json
import re

from openai import AsyncOpenAI
from typing import List, Dict, Any
from api.grading.schemas.subjective_grading import GradingCriterion

from dotenv import load_dotenv
from src.agents.test_feedback.prompt import SYSTEM_PROMPT, build_user_prompt
from src.agents.test_feedback.tools.document_performance import calc_performance_by_document
from src.agents.test_feedback.tools.question_selector import select_top_bottom_questions


#openai 로드
load_dotenv(override=True) 
api_key = os.getenv("OPENAI_API_KEY") 
openai_client = AsyncOpenAI(api_key=api_key) 
AGENT_MODEL = os.getenv("AGENT_TEST_FEEDBACK_MODEL") #.env에 모델명 저장 (AGENT_TEST_FEEDBACK_MODEL=gpt-4)✅

#gemini 로드
# load_dotenv(override=True) 
# gemini_api_key = os.getenv("GEMINI_API_KEY") 
# gemini_client = genai.Client(api_key=gemini_api_key)
# GEMINI_MODEL = os.getenv("GEMINI_AGENT_TEST_FEEDBACK_MODEL") #.env에 모델명 저장 (GEMINI_AGENT_TEST_FEEDBACK_MODEL=gemini-2.5-flash)✅


async def test_feedback(exam_goal: str, question_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    OpenAI를 이용하여 시험목표와 문항별 응시 결과를 분석하고 종합적인 피드백을 반환
    """
    # 1. 사전 데이터 계산
    performance_by_document, project_readiness_result = calc_performance_by_document(question_results)
    selected_questions = select_top_bottom_questions(question_results)

    # 2. 최종 프롬프트 구성 (선택된 문제만 전달)
    USER_PROMPT = build_user_prompt(exam_goal, selected_questions, performance_by_document, project_readiness_result)

    # 3. MODEL 호출
    try:
        # RAW INPUT 출력 #########################################
        # print("\n" + "="*80)
        # print("🤖 MODEL INPUT (RAW)")
        # print("="*80)
        # messages=[
        #         {"role": "system", "content": SYSTEM_PROMPT},
        #         {"role": "user", "content": USER_PROMPT}
        #     ]
        # print(messages)
        ########################################################
        
        #OPENAI 방식
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


        #GEMINI 방식
        # response = gemini_client.models.generate_content(
        #     model=GEMINI_MODEL,
        #     contents=[
        #         {"role": "model", "parts": [{"text": SYSTEM_PROMPT}]},
        #         {"role": "user", "parts": [{"text": USER_PROMPT}]}
        #     ],
        # )
        # content = response.text.strip()
        # if content.startswith("```"):
        #     content = re.sub(r"^```(?:json)?\s*", "", content)  # 앞쪽 제거
        #     content = re.sub(r"\s*```$", "", content)           # 뒤쪽 제거
        

        # RAW OUTPUT 출력 #########################################
        # print("\n" + "="*80)
        # print("🤖 MODEL OUTPUT (RAW)")
        # print("="*80)
        # print(content)
        # print("="*80)
        ########################################################

        result = json.loads(content)

        # 4. AI 결과 후처리
        # 4-1. projectReadiness를 문서별 최소 정답률 기준으로 계산하여 결과에 추가
        result['projectReadiness'] = project_readiness_result
        
        # 4-2. averageCorrectRate만 실제 값으로 덮어쓰기
        doc_rate_map = {doc['documentName']: doc['averageCorrectRate'] for doc in performance_by_document}
        for doc in result.get('performanceByDocument', []):
            name = doc.get('documentName')
            if name in doc_rate_map:
                doc['averageCorrectRate'] = doc_rate_map[name]

        # 토큰 사용량 (차후 주석처리 ✅ )
        usage = response.usage
        print("🟨 사용 토큰:", usage.total_tokens)
        print("└─ prompt_tokens:", usage.prompt_tokens)
        print("└─ completion_tokens:", usage.completion_tokens)
        
        return result

    except Exception as e:
        raise RuntimeError(f"시험 피드백 생성 오류: {str(e)}")