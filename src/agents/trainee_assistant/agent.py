from openai import AsyncOpenAI

from api.trainee_assistant.schemas.trainee_assistant import Question

openai_client = AsyncOpenAI()


async def answer_based_on_question_data(
    user_question: str, question_data: Question
) -> str:
    """
    사용자의 질문과 해당 문제의 Question 데이터를 바탕으로 GPT가 직접 답변 생성
    """
    context = f"""
[문제 정보]
- 질문: {question_data.question}
- 정답: {question_data.answer}
- 해설: {question_data.explanation or "없음"}
- 객관식 보기: {", ".join(question_data.options or []) or "없음"}
- 채점 기준: {", ".join(gc.criteria for gc in question_data.gradingCriteria or []) or "없음"}
- 관련 문서명: {question_data.documentName or "없음"}
- 키워드: {", ".join(question_data.keywords or []) or "없음"}
- 태그: {", ".join(question_data.tags or []) or "없음"}
    """.strip()

    system_prompt = (
        "당신은 교육 AI 비서입니다. 아래 문제 정보를 참고하여 사용자의 질문에 맞는 정보를 제공하세요.\n"
        "- 질문이 정답을 묻는 것이라면 정답을,\n"
        "- 해설을 묻는 것이라면 해설을,\n"
        "- 문서를 묻는 것이라면 documentName을 기반으로 설명을,\n"
        "- 키워드나 태그, 채점 기준 등 다른 속성에 대한 질문도 자연스럽게 응답하세요.\n"
        "불명확한 질문에는 친절히 되묻거나, 관련된 정보로 최대한 도움을 주세요."
    )

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context}\n\n[사용자 질문]\n{user_question}"},
        ],
    )

    return response.choices[0].message.content.strip()
