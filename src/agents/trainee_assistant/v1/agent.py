# agents/trainee_assistant/agent.py

from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI

from agents.trainee_assistant.v1.prompt import SYSTEM_PROMPT, build_user_prompt
from config.settings import settings
from db.redisDB.session_manager import append_message, load_message_history

# OpenAI 로드
api_key = settings.api_key
openai_client = wrap_openai(AsyncOpenAI(api_key=api_key))
AGENT_MODEL = settings.subjective_grader_model


@traceable(
    run_type="chain",
    name="Trainee Assistant Chat",
    metadata={"agent_type": "trainee_assistant"},
)
async def trainee_assistant_chat(
    user_question: str, question_info: dict, message_history: list
) -> str:
    """
    Trainee Assistant 챗봇 - 시험 문제 관련 질문에 답변
    user_question: str - 사용자의 질문
    question_info: dict - 문항 정보
    message_history: list - 이전 대화 내역
    """
    USER_PROMPT = build_user_prompt(user_question, question_info, message_history)

    try:
        # RAW INPUT 출력 #########################################
        print("\n" + "=" * 80)
        print("🤖 MODEL INPUT (RAW)")
        print("=" * 80)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT},
        ]
        print(messages)
        ########################################################

        response = await openai_client.chat.completions.create(
            model="AGENT_MODEL",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT},
            ],
            temperature=0.2,
            stream=False,
        )
        content = response.choices[0].message.content.strip()

        return content

    except Exception as e:
        raise RuntimeError(f"챗봇 오류: {str(e)}")


# FastAPI 라우터용 함수
@traceable(
    run_type="chain",
    name="Get Chat Response",
    metadata={"agent_type": "trainee_assistant"},
)
async def get_chat_response(
    user_id: str, user_question: str, question_info: dict
) -> str:
    message_history = await load_message_history(user_id)
    await append_message(user_id, "user", user_question)

    response = await trainee_assistant_chat(
        user_question, question_info, message_history
    )

    await append_message(user_id, "assistant", response)
    return response
