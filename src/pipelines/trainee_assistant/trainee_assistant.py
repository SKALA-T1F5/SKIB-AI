import asyncio
import logging
from typing import List

from konlpy.tag import Okt
from langgraph.graph import StateGraph
from langsmith import traceable
from openai import AsyncOpenAI

from api.trainee_assistant.schemas.trainee_assistant import Question
from config.settings import settings
from db.redisDB.session_manager import append_message, load_message_history
from db.vectorDB.chromaDB.search import search_similar
from src.agents.trainee_assistant.agent import answer_based_on_question_data
from src.agents.trainee_assistant.prompt_1 import (
    build_prompt_from_docs,
    system_prompt_no_context,
)
from src.pipelines.trainee_assistant.state import ChatState

logger = logging.getLogger(__name__)

openai_client = AsyncOpenAI(api_key=settings.api_key)
okt = Okt()


@traceable(
    run_type="tool",
    name="Extract Keywords",
    metadata={"tool_type": "keyword_extraction"},
)
def extract_keywords(text: str, top_k: int = 5) -> List[str]:
    words = [
        word
        for word, pos in okt.pos(text)
        if pos in ["Noun", "Alpha", "Verb"] and len(word) > 1
    ]
    from collections import Counter

    return [word for word, _ in Counter(words).most_common(top_k)]


@traceable(
    run_type="chain",
    name="Vector Search Node",
    metadata={"pipeline": "trainee_assistant", "node_type": "vector_search"},
)
def vector_search_node(state: ChatState) -> ChatState:
    question_data = next(
        (q for q in state["test_questions"] if q.id == state["question_id"]), None
    )

    if not question_data:
        logger.warning("❌ 질문 ID에 해당하는 테스트 문제를 찾을 수 없습니다.")
        return {"chroma_docs": [], "document_name": None}

    document_name = question_data.documentName
    keywords = extract_keywords(state["question"])

    logger.info(f"🔍 ChromaDB에서 검색 수행: document_name={document_name}")
    docs = search_similar(
        query=state["question"], collection_name=document_name, n_results=5
    )

    MIN_SIMILARITY = 0.75
    filtered_docs = [
        doc
        for doc in docs
        if doc["similarity"] >= MIN_SIMILARITY
        and any(k in doc["content"] for k in keywords)
    ]

    if filtered_docs:
        logger.info(f"📄 관련 문서 {len(filtered_docs)}개 발견")
    else:
        logger.warning("⚠️ 문서는 있으나 관련된 내용을 찾지 못함")

    return {"chroma_docs": filtered_docs, "document_name": document_name}


def generate_direct_answer_or_explanation(intent: str, question_data: Question) -> str:
    if intent == "answer":
        return f"📌 해당 문제의 정답은 다음과 같습니다:\n\n{question_data.answer}"
    elif intent == "explanation" and question_data.explanation:
        return f"💡 해당 문제의 해설은 다음과 같습니다:\n\n{question_data.explanation}"
    return None


@traceable(
    run_type="chain",
    name="Generate Answer Node",
    metadata={
        "pipeline": "trainee_assistant",
        "node_type": "answer_generation",
        "model": "gpt-4o",
    },
)
async def generate_answer_node(state: ChatState) -> ChatState:
    history = await load_message_history(state["user_id"])
    history.append({"role": "user", "content": state["question"]})

    question_data = next(
        (q for q in state["test_questions"] if q.id == state["question_id"]), None
    )

    if question_data:
        answer = await answer_based_on_question_data(state["question"], question_data)
        await append_message(state["user_id"], "user", state["question"])
        await append_message(state["user_id"], "assistant", answer)
        return {"answer": answer}

    if state.get("chroma_docs"):
        prompt = build_prompt_from_docs(state["question"], state["chroma_docs"])
        prompt_role = {"role": "user", "content": prompt}
    else:
        warning = "⚠️ 관련 문서를 찾을 수 없어 일반적인 답변을 제공합니다."
        prompt_role = {
            "role": "user",
            "content": f"{warning}\n\n[사용자 질문]\n{state['question']}",
        }

    logger.info("🤖 GPT 호출 시작")
    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": system_prompt_no_context.strip(),
            },
            *history,
            prompt_role,
        ],
    )
    answer = response.choices[0].message.content
    logger.info("💬 GPT 응답 수신 완료")

    if state.get("chroma_docs"):
        source_info = f"\n\n📝 (출처: 문서 '{state['document_name']}')"
        answer += source_info

    await append_message(state["user_id"], "user", state["question"])
    await append_message(state["user_id"], "assistant", answer)
    logger.info("📝 대화 내용 Redis 저장 완료")

    return {"answer": answer}


@traceable(
    run_type="chain",
    name="Build Trainee Assistant Pipeline",
    metadata={"pipeline": "trainee_assistant", "graph_type": "langgraph"},
)
def build_langgraph():
    builder = StateGraph(ChatState)

    builder.add_node("vector_search_node", vector_search_node)
    builder.add_node("generate_answer_node", generate_answer_node)

    builder.set_entry_point("vector_search_node")
    builder.add_edge("vector_search_node", "generate_answer_node")

    return builder.compile()
