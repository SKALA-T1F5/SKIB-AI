# agents/test_feedback/agent.py
import json
import os
import re
from typing import Any, Dict, List

import google.generativeai as genai
from dotenv import load_dotenv
from langsmith import traceable

from src.agents.test_feedback.prompt import SYSTEM_PROMPT, build_user_prompt
from src.agents.test_feedback.tools.document_performance import (
    calc_performance_by_document,
)
from src.agents.test_feedback.tools.question_selector import select_top_bottom_questions

# model 로드
load_dotenv(override=True)
gemini_api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=gemini_api_key)
GEMINI_MODEL = os.getenv(
    "GEMINI_AGENT_TEST_FEEDBACK_MODEL"
)  # .env에 모델명 저장 (GEMINI_AGENT_TEST_FEEDBACK_MODEL=gemini-2.5-flash-lite-preview-06-17)✅


@traceable(
    run_type="chain",
    name="Test Feedback",
    metadata={"agent_type": "test_feedback"}
)
async def test_feedback(
    exam_goal: str, question_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    OpenAI를 이용하여 시험목표와 문항별 응시 결과를 분석하고 종합적인 피드백을 반환
    """

    # 1. 사전 데이터 계산
    performance_by_document, project_readiness_result = calc_performance_by_document(
        question_results
    )
    selected_questions = select_top_bottom_questions(question_results)

    # 2. 최종 프롬프트 구성 (선택된 문제만 전달)
    USER_PROMPT = build_user_prompt(
        exam_goal, selected_questions, performance_by_document, project_readiness_result
    )

    model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-06-17")

    # 3. MODEL 호출
    try:
        response = model.generate_content(
            contents=[
                {"role": "model", "parts": [{"text": SYSTEM_PROMPT}]},
                {"role": "user", "parts": [{"text": USER_PROMPT}]},
            ],
        )
        content = response.text.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        result = json.loads(content)

        # 4. AI 결과 후처리
        # 4-1. projectReadiness를 문서별 최소 정답률 기준으로 계산하여 결과에 추가
        result["projectReadiness"] = project_readiness_result

        # 4-2. averageCorrectRate만 실제 값으로 덮어쓰기
        doc_rate_map = {
            doc["documentName"]: doc["averageCorrectRate"]
            for doc in performance_by_document
        }
        for doc in result.get("performanceByDocument", []):
            name = doc.get("documentName")
            if name in doc_rate_map:
                doc["averageCorrectRate"] = doc_rate_map[name]

        return result

    except Exception as e:
        raise RuntimeError(f"시험 피드백 생성 오류: {str(e)}")
