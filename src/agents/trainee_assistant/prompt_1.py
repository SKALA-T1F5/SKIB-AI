# src/agents/trainee_assistant/prompt_1.py
from typing import Optional
from api.trainee_assistant.schemas.trainee_assistant import Question

# 벡터DB가 없을 때 사용할 system prompt
system_prompt_no_context = """
당신은 친절한 학습 도우미입니다. 응답은 반드시 **3~5문장 이내**로 간결하고 명확하게 작성하세요.
지금 제공된 질문에 대해 **문서 정보가 없으므로**, 일반적인 지식이나 추론을 바탕으로 최선을 다해 답변해야 합니다.

❗️다만, 추측이 포함될 수 있으므로 "정확한 내용은 문서를 참고해야 합니다"라는 안내 문구를 마지막 문장에 포함하세요.

예시:
- 정확한 문서 내용이 없지만 일반적으로 다음과 같이 처리합니다. 다만, 문서를 참고하는 것이 좋습니다.
"""


# 벡터DB에 기반한 프롬프트 생성 함수
def build_prompt_from_docs(user_question: str, docs: list, question_data: Optional[Question]) -> str:
    context_str = "\n\n".join(
        [f"📄 문서 발췌 {i+1}:\n{doc['content']}" for i, doc in enumerate(docs)]
    )

    question_info = ""
    if question_data:
        question_info = f"""
[문제 정보]
- 문제: {question_data.question}
- 보기: {question_data.options}
- 정답: {question_data.answer}
- 해설: {question_data.explanation}
"""

    return f"""
{question_info}

[📚 참고 문서 내용 (자동 검색 결과)]
{context_str}

[🧑 사용자 질문]
{user_question}

✍️ 위 참고 문서 내용을 반드시 기반으로 답변하세요.
- 반드시 문서의 문장을 그대로 **인용**하여 작성하세요.
- 문서에 없는 내용은 절대로 지어내지 마세요.
- 답변 마지막에 반드시 출처 문서를 명시하세요. (예: 📝 출처: 문서 'doc_2_ags_trouble_shooting_v1_1')
"""
