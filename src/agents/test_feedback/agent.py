# agents/test_feedback/agent.py
import os
import openai
import json
from collections import defaultdict

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

def calc_performance_by_document(question_results: List[Dict[str, Any]]):
    doc_map = defaultdict(list)
    for q in question_results:
        doc_map[q['documentName']].append(q)
    performance = []
    for doc, questions in doc_map.items():
        avg = sum(q['correctRate'] for q in questions) / len(questions)
        keywords = list({q['keyword'] for q in questions if 'keyword' in q})
        performance.append({
            "documentName": doc,
            "averageCorrectRate": round(avg, 2),
            "keywords": keywords
            # comment는 AI가 생성
        })
    return performance

async def test_feedback(exam_goal: str, question_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    OpenAI를 이용하여 시험목표와 문항별 응시 결과를 분석하고 종합적인 피드백을 반환
    """
    # 1. 문서별 평균 정답률 계산
    performance_by_document = calc_performance_by_document(question_results)

    # 2. 최종 프롬프트 구성
    # USER_PROMPT = build_user_prompt(exam_goal, question_results)
    # 2. 최종 프롬프트 구성 (A: 프롬프트에 포함)
    USER_PROMPT = build_user_prompt(exam_goal, question_results, performance_by_document)

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
        # print("\n" + "="*80)
        # print("🤖 MODEL OUTPUT (RAW)")
        # print("="*80)
        # print(content)
        # print("="*80)
        ########################################################

        result = json.loads(content)

        # 4. 실제 값으로 덮어쓰기
        result['performanceByDocument'] = performance_by_document

        # 토큰 사용량 (차후 주석처리 ✅ )
        usage = response.usage
        print("🟨 사용 토큰:", usage.total_tokens)
        print("└─ prompt_tokens:", usage.prompt_tokens)
        print("└─ completion_tokens:", usage.completion_tokens)
        
        return result

    except Exception as e:
        raise RuntimeError(f"시험 피드백 생성 오류: {str(e)}")