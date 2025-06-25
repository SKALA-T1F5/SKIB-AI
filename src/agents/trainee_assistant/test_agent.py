# agents/trainee_assistant/test_agent.py
import sys
import os
import asyncio
import copy
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.agents.trainee_assistant.agent import trainee_assistant_chat
from src.agents.trainee_assistant.example_data.example_data_1 import example_inputs

async def main():
    print("🤖 채점 문제 Q&A 챗봇입니다. (종료: exit, quit, 종료)")
    # 첫 번째 example_inputs만 사용
    example = copy.deepcopy(example_inputs[0])
    history = example['messageHistory']
    question_info = example['questionInfo']
    print(f"\n문제: {question_info['question']}")
    while True:
        # ====== 채팅(대화) 처리 영역 ======
        user_input = input("\n질문: ").strip()
        if user_input.lower() in ['exit', 'quit', '종료']:
            print("챗봇을 종료합니다.")
            break
        if not user_input:
            print("질문을 입력해주세요.")
            continue
        print("답변 생성 중...\n")
        # ====== example_data_1.py의 messageHistory 업데이트 영역 ======
        history.append({"role": "user", "content": user_input})
        try:
            answer = await trainee_assistant_chat(user_input, question_info, history)
            print(f"🤖 답변: {answer}\n")
            # ====== example_data_1.py의 messageHistory 업데이트 영역 ======
            history.append({"role": "assistant", "content": answer})
        except Exception as e:
            print(f"오류: {e}")

if __name__ == "__main__":
    asyncio.run(main())

