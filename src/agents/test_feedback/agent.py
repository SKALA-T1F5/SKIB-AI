# agents/test_feedback/agent.py
import json
import re
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# import google.generativeai as genai
from langsmith import traceable

from src.agents.test_feedback.prompt import SYSTEM_PROMPT, build_user_prompt
from src.agents.test_feedback.tools.document_performance import (
    calc_performance_by_document,
)
from src.agents.test_feedback.tools.question_selector import select_top_bottom_questions


@traceable(
    run_type="chain", name="Test Feedback", metadata={"agent_type": "test_feedback"}
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

    # GENAI ver.
    # model = genai.GenerativeModel("gemini-2.5-flash-lite-preview-06-17")

    # 3. ChatGoogleGenerativeAI 초기화
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-lite-preview-06-17",
        temperature=0.3,
        max_output_tokens=3000,
        max_retries=2,
        timeout=60,
    )

    # 4. ChatPromptTemplate 사용
    prompt_template = ChatPromptTemplate.from_messages(
        [("system", "{system_prompt}"), ("human", "{user_prompt}")]
    )

    try:
        # GENAI ver.
        # response = model.generate_content(
        #     contents=[
        #         {"role": "model", "parts": [{"text": SYSTEM_PROMPT}]},
        #         {"role": "user", "parts": [{"text": USER_PROMPT}]},
        #     ],
        # )
        # content = response.text.strip()

        # 5. 체인 생성 및 실행
        chain = prompt_template | llm
        response = await chain.ainvoke(
            {"system_prompt": SYSTEM_PROMPT, "user_prompt": USER_PROMPT}
        )

        # 6. 응답 처리
        content = response.content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        result = json.loads(content)

        # 7. AI 결과 후처리
        # 7-1. projectReadiness를 문서별 최소 정답률 기준으로 계산하여 결과에 추가
        result["projectReadiness"] = project_readiness_result

        # 7-2. averageCorrectRate만 실제 값으로 덮어쓰기
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
