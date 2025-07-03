import json
import logging
from typing import List

from konlpy.tag import Okt
from langgraph.graph import StateGraph
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import AsyncOpenAI

from config.settings import settings
from db.redisDB.session_manager import append_message, load_message_history
from db.vectorDB.chromaDB.search import search_similar
from src.agents.trainee_assistant.prompt_1 import (
    build_prompt_from_docs,
    system_prompt_no_context,
)
from src.pipelines.trainee_assistant.state import ChatState

logger = logging.getLogger(__name__)

okt = Okt()


def get_openai_client():
    api_key = settings.api_key
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set.")
    return wrap_openai(AsyncOpenAI(api_key=api_key))


openai_client = get_openai_client()


@traceable(
    run_type="tool",
    name="Extract Keywords",
    metadata={"tool_type": "keyword_extraction"},
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


# --- Graph Nodes ---


async def route_question(state: ChatState) -> str:
    """사용자의 질문 의도를 파악하여 다음 단계를 결정하는 라우터 노드"""
    user_question = state["question"]
    question_data = next(
        (q for q in state["test_questions"] if q.id == state["question_id"]), None
    )

    if not question_data:
        logger.warning("❌ 질문 ID에 해당하는 테스트 문제를 찾을 수 없습니다.")
        return "end"  # or some error handling state

    # Update state with the found question_data
    state["question_data"] = question_data

    prompt = f"""당신은 질문의 의도를 파악하는 라우팅 전문가입니다. 주어진 [문제 정보]와 [사용자 질문]을 보고, 질문의 의도를 다음 두 가지 중 하나로 분류하세요.

[문제 정보]
- 문제: {question_data.question}
- 유형: {question_data.type.value}
- 정답: {question_data.answer}
- 해설: {question_data.explanation}

[사용자 질문]
{user_question}

[분류]
1. `direct_answer`: 사용자가 문제의 정답, 보기, 해설, 유형 등 제공된 [문제 정보]에 대해 직접적으로 묻고 있습니다.
   (예: "정답이 뭐야?", "해설 보여줘", "이 문제 무슨 유형이야?")
2. `document_search`: 사용자가 문제의 배경, 개념, 이유 등 [문제 정보]에 직접적으로 명시되지 않은, 더 깊은 내용을 묻고 있습니다. 이 경우 관련 문서를 찾아봐야 합니다.
   (예: "왜 이게 정답이야?", "AGS Trouble shooting 가이드가 뭐야?", "탄소배출권이 뭐야?")

오직 `direct_answer` 또는 `document_search` 둘 중 하나로만 답변하세요."""

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    route = response.choices[0].message.content.strip()
    logger.info(f"🚦 라우팅 결정: {route}")
    return route


async def generate_direct_answer_node(state: ChatState) -> ChatState:
    """문제 데이터(question_data)를 기반으로 직접 답변을 생성하는 노드"""
    user_question = state["question"]
    question_data = state["question_data"]

    prompt = f"""당신은 친절한 학습 도우미입니다. 주어진 [문제 정보]를 바탕으로 [사용자 질문]에 대해 간결하고 명확하게 답변하세요.

[문제 정보]
{json.dumps(question_data.dict(), ensure_ascii=False, indent=2)}

[사용자 질문]
{user_question}

절대로 [문제 정보]에 없는 내용을 지어내지 마세요."""

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    answer = response.choices[0].message.content
    logger.info("💬 (Direct) GPT 응답 수신 완료")

    await append_message(state["user_id"], "user", user_question)
    await append_message(state["user_id"], "assistant", answer)
    logger.info("📝 (Direct) 대화 내용 Redis 저장 완료")

    return {"answer": answer}


def vector_search_node(state: ChatState) -> ChatState:
    """관련 문서를 벡터DB에서 검색하는 노드"""
    document_name = state["question_data"].documentName
    logger.info(f"🔍 ChromaDB에서 검색 수행: document_name={document_name}")
    docs = search_similar(
        query=state["question"], collection_name=document_name, n_results=5
    )

    MIN_SIMILARITY = 0.75
    filtered_docs = [doc for doc in docs if doc["similarity"] >= MIN_SIMILARITY]

    if filtered_docs:
        logger.info(f"📄 관련 문서 {len(filtered_docs)}개 발견")
    else:
        logger.warning("⚠️ 문서는 있으나 관련된 내용을 찾지 못함")

    return {"chroma_docs": filtered_docs, "document_name": document_name}


async def generate_document_based_answer_node(state: ChatState) -> ChatState:
    """벡터DB 검색 결과를 바탕으로 답변을 생성하는 노드"""
    user_question = state["question"]
    history = await load_message_history(state["user_id"])
    history.append({"role": "user", "content": user_question})

    if state.get("chroma_docs"):
        prompt = build_prompt_from_docs(
            user_question, state["chroma_docs"], state["question_data"]
        )
        prompt_role = {"role": "user", "content": prompt}
        answer_prefix = ""
    else:
        warning = "⚠️ 관련 문서를 찾을 수 없어 일반적인 답변을 제공합니다."
        prompt_role = {
            "role": "user",
            "content": f"{warning}\n\n[사용자 질문]\n{user_question}",
        }
        answer_prefix = "관련 정보를 찾지 못해 LLM이 일반적인 지식으로 답변합니다.\n\n"

    logger.info("🤖 (Doc-Based) GPT 호출 시작")
    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt_no_context.strip()},
            *history,
            prompt_role,
        ],
    )
    answer = response.choices[0].message.content
    logger.info("💬 (Doc-Based) GPT 응답 수신 완료")

    answer = answer_prefix + answer
    if state.get("chroma_docs"):
        answer += f"\n\n📝 (출처: 문서 '{state['document_name']}')"

    await append_message(state["user_id"], "user", user_question)
    await append_message(state["user_id"], "assistant", answer)
    logger.info("📝 (Doc-Based) 대화 내용 Redis 저장 완료")

    return {"answer": answer}


# --- Graph Builder ---
@traceable(
    run_type="chain",
    name="Build Trainee Assistant Pipeline",
    metadata={"pipeline": "trainee_assistant", "graph_type": "langgraph"},
)
def build_langgraph():
    builder = StateGraph(ChatState)

    builder.add_node("route_question", route_question)
    builder.add_node("generate_direct_answer_node", generate_direct_answer_node)
    builder.add_node("vector_search_node", vector_search_node)
    builder.add_node(
        "generate_document_based_answer_node", generate_document_based_answer_node
    )

    builder.set_entry_point("route_question")

    builder.add_conditional_edges(
        "route_question",
        lambda x: x,
        {
            "direct_answer": "generate_direct_answer_node",
            "document_search": "vector_search_node",
        },
    )

    builder.add_edge("vector_search_node", "generate_document_based_answer_node")
    builder.add_edge("generate_direct_answer_node", END)
    builder.add_edge("generate_document_based_answer_node", END)

    return builder.compile()
