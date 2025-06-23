# agents/test_feedback/agent.py
import os
import openai
from google import genai
import json
from collections import defaultdict
import re

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

#gemini 로드
# load_dotenv(override=True) 
gemini_api_key = os.getenv("GEMINI_API_KEY") 
gemini_client = genai.Client(api_key=gemini_api_key)
GEMINI_MODEL = os.getenv("GEMINI_AGENT_TEST_FEEDBACK_MODEL") #.env에 모델명 저장 (GEMINI_AGENT_TEST_FEEDBACK_MODEL=gemini-2.5-flash)✅


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
            "countQuestions": len(questions),  # 문서별 총 문제 개수 추가
            "keywords": keywords
        })
    return performance

def select_top_bottom_questions(question_results: List[Dict[str, Any]], top_count: int = 5, bottom_count: int = 5) -> List[Dict[str, Any]]:
    """
    전체 문제 중 정답률 기준 상위 5개, 하위 5개 문제를 선택하여 총 10개 문제를 반환
    """
    # 정답률 기준으로 전체 문제 정렬
    sorted_questions = sorted(question_results, key=lambda x: x['correctRate'], reverse=True)
    
    selected_questions = []
    
    # 상위 5개 선택
    top_questions = sorted_questions[:top_count]
    selected_questions.extend(top_questions)
    
    # 하위 5개 선택 (중복 방지)
    if len(sorted_questions) > top_count + bottom_count:
        bottom_questions = sorted_questions[-(bottom_count):]
    elif len(sorted_questions) > top_count:
        bottom_questions = sorted_questions[top_count:]
    else:
        bottom_questions = []
    
    selected_questions.extend(bottom_questions)
    
    return selected_questions

def extract_json_from_gemini(content: str) -> str:
    # 코드블록 내 JSON 추출
    match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", content)
    if match:
        return match.group(1)
    # 일반 코드블록 (json 명시X)
    match = re.search(r"```\s*(\{[\s\S]*?\})\s*```", content)
    if match:
        return match.group(1)
    # 중괄호로 시작하는 첫 JSON 객체 추출
    match = re.search(r"(\{[\s\S]*\})", content)
    if match:
        return match.group(1)
    # 그대로 반환 (마지막 수단)
    return content.strip()

async def test_feedback(exam_goal: str, question_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    OpenAI를 이용하여 시험목표와 문항별 응시 결과를 분석하고 종합적인 피드백을 반환
    """
    # 1. 사전 데이터 계산
    performance_by_document = calc_performance_by_document(question_results)
    selected_questions = select_top_bottom_questions(question_results)

    # 2. 최종 프롬프트 구성
    USER_PROMPT = build_user_prompt(exam_goal, selected_questions, performance_by_document)

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
        # response = await openai_client.chat.completions.create(
        #     model=AGENT_MODEL,
        #     messages=[
        #         {"role": "system", "content": SYSTEM_PROMPT},
        #         {"role": "user", "content": USER_PROMPT}
        #     ],
        #     temperature=0.2,
        #     stream=False,
        # )
        # content = response.choices[0].message.content.strip()


        #GEMINI 방식
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                {"role": "model", "parts": [{"text": SYSTEM_PROMPT}]},
                {"role": "user", "parts": [{"text": USER_PROMPT}]}
            ],
        )
        content = response.text
        content = response.choices[0].message.content.strip()
        # Gemini 등 LLM의 코드블록/텍스트 혼합 응답에서 JSON만 추출
        content = extract_json_from_gemini(content)
        try:
            result = json.loads(content)
        except Exception as e:
            print("AI 원본 응답:", content)
            raise RuntimeError(f"시험 피드백 생성 오류: {str(e)}")
        

        # RAW OUTPUT 출력 #########################################
        print("\n" + "="*80)
        print("🤖 MODEL OUTPUT (RAW)")
        print("="*80)
        print(content)
        print("="*80)
        ########################################################

        result = json.loads(content)

        # 4. AI 결과 후처리
        # 4-1. projectReadiness를 문서별 최소 정답률 기준으로 계산하여 결과에 추가
        min_rate = min(doc['averageCorrectRate'] for doc in performance_by_document) if performance_by_document else 0
        if min_rate >= 90:
            project_readiness_result = "Excellent"
        elif min_rate >= 60:
            project_readiness_result = "Pass"
        else:
            project_readiness_result = "Fail"
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