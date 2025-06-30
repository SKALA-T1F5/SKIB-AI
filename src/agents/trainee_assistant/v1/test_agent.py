import asyncio
import copy
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from agents.trainee_assistant.v1.agent import get_chat_response
from src.agents.trainee_assistant.example_data.example_data_1 import example_inputs


async def main():
    print("🤖 채점 문제 Q&A 챗봇입니다. (종료: exit, quit, 종료)")
    example = copy.deepcopy(example_inputs[0])
    question_info = example["questionInfo"]
    user_id = "test-user-001"  # ✅ 사용자별 세션 구분용 ID

    print(f"\n문제: {question_info['question']}")
    while True:
        user_input = input("\n질문: ").strip()
        if user_input.lower() in ["exit", "quit", "종료"]:
            print("챗봇을 종료합니다.")
            break
        if not user_input:
            print("질문을 입력해주세요.")
            continue
        print("답변 생성 중...\n")
        try:
            answer = await get_chat_response(user_id, user_input, question_info)
            print(f"🤖 답변: {answer}\n")
        except Exception as e:
            print(f"오류: {e}")


if __name__ == "__main__":
    asyncio.run(main())
