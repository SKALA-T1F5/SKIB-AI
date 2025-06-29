# agents/initializer.py

from langchain.schema import BaseMessage
from langchain_core.runnables import Runnable
from openai import AsyncOpenAI

from config.settings import settings

client = AsyncOpenAI(api_key=settings.api_key)


async def init_prompt_with_test_info(test_info: list):
    test_intro = "\n".join(
        [f"{q['id']}. {q['question']} ({q['type']})" for q in test_info]
    )
    prompt = f"""다음은 학습자가 본 테스트 문항입니다:\n{test_intro}\n\n이 정보를 기반으로 이후 질문에 컨텍스트를 유지하세요."""

    response = await client.chat.completions.create(
        model=settings.subjective_grader_model,
        messages=[
            {"role": "system", "content": "친절한 학습 도우미입니다."},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content
