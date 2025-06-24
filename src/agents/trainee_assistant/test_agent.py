# test_agent.py
import asyncio
from src.agents.trainee_assistant.agent import TraineeAssistantAgent

async def main():
    agent = TraineeAssistantAgent()

    # 문제 정보 세팅 (옵션)
    question_data = {
    "_id": "dummy_question_id",  # ✅ 추가
    "test_id": "t1",
    "question_id": "q1",
    "question_type": "objective",
    "difficulty_level": "normal",
    "question_text": "다음 중 AI가 아닌 것은?",
    "options": ["ChatGPT", "Bard", "AlphaGo", "엑셀"],
    "correct_answer": "엑셀",
    "explanation": "엑셀은 전통적인 소프트웨어이며 생성형 AI가 아니다.",
    "document_id": "doc1",
    "document_name": "ai_intro",
    "tags": ["AI", "기초"]
}
    agent.set_question_context(question_data)

    # 메시지 전송
    user_input = "Where is the Eiffel Tower located?"
    result = await agent.process_message(user_input)

    print("\n🟢 응답:")
    print(result["response"])

    print("\n🟡 워크플로우 정보:")
    print(result["workflow_info"])

    print("\n🔵 대화 요약:")
    print(agent.get_conversation_summary())

# 비동기 실행
if __name__ == "__main__":
    asyncio.run(main())