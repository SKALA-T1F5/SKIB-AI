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
    metadata={"tool_type": "keyword_extraction"}
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
    metadata={"pipeline": "trainee_assistant", "node_type": "vector_search"}
)
def vector_search_node(state: ChatState) -> ChatState:
    question_data = next(
        (q for q in state["test_questions"] if q.id == state["question_id"]), None
    )
    if not question_data:
        logger.warning("❌ 질문 ID에 해당하는 테스트 문제를 찾을 수 없습니다.")
        return {"chroma_docs": [], "document_name": None, "question_data": None}

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

    return {
        "chroma_docs": filtered_docs,
        "document_name": document_name,
        "question_data": question_data,
    }


@traceable(
    run_type="chain",
    name="Generate Answer Node",
    metadata={"pipeline": "trainee_assistant", "node_type": "answer_generation", "model": "gpt-4o"}
)
async def generate_answer_node(state: ChatState) -> ChatState:
    user_question = state["question"]
    question_data = state["question_data"]

    # 사용자의 질문 의도 파악 (단순 정보 조회)
    if question_data:
        keyword_map = {
            ("문제",): (lambda q: f"문제 내용은 다음과 같습니다:\n\n{q.question}"),
            ("유형", "타입"): (lambda q: f"이 문제의 유형은 '{q.type.value}'입니다."),
            ("난이도",): (lambda q: f"이 문제의 난이도는 '{q.difficultyLevel}'입니다." if q.difficultyLevel else "난이도가 설정되지 않았습니다."),
            ("보기", "선택지"): (lambda q: f"선택지는 다음과 같습니다:\n{', '.join(q.options)}" if q.options else "객관식 문제가 아니거나 선택지가 없습니다."),
            ("정답", "답"): (lambda q: f"정답은 '{q.answer}'입니다."),
            ("해설",): (lambda q: q.explanation or "해설이 제공되지 않았습니다."),
            ("채점 기준",): (lambda q: f"채점 기준은 다음과 같습니다:\n{json.dumps([item.dict() for item in q.gradingCriteria], ensure_ascii=False, indent=2)}" if q.gradingCriteria else "주관식 문제가 아니거나 채점 기준이 없습니다."),
            ("문서 ID", "문서 아이디"): (lambda q: f"관련 문서 ID는 '{q.documentId}'입니다."),
            ("문서 이름", "문서명"): (lambda q: f"관련 문서 이름은 '{q.documentName}'입니다."),
            ("키워드",): (lambda q: f"관련 키워드는 다음과 같습니다:\n{', '.join(q.keywords)}" if q.keywords else "관련 키워드가 없습니다."),
            ("태그",): (lambda q: f"관련 태그는 다음과 같습니다:\n{', '.join(q.tags)}" if q.tags else "관련 태그가 없습니다."),
            ("생성 타입", "생성 유형"): (lambda q: f"문제 생성 유형은 '{q.generationType.value}'입니다."),
        }

        for keywords, response_func in keyword_map.items():
            if any(keyword in user_question for keyword in keywords):
                answer = response_func(question_data)
                await append_message(state["user_id"], "user", user_question)
                await append_message(state["user_id"], "assistant", answer)
                logger.info("📝 (Direct) 대화 내용 Redis 저장 완료")
                return {"answer": answer}

    # If no direct answer was generated, proceed with LLM call
    history = await load_message_history(state["user_id"])
    history.append({"role": "user", "content": user_question})

    if state.get("chroma_docs"):
        prompt = build_prompt_from_docs(
            user_question, state["chroma_docs"], question_data
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

    answer = answer_prefix + answer

    if state.get("chroma_docs"):
        source_info = f"\n\n📝 (출처: 문서 '{state['document_name']}')"
        answer += source_info

    await append_message(state["user_id"], "user", user_question)
    await append_message(state["user_id"], "assistant", answer)
    logger.info("📝 대화 내용 Redis 저장 완료")

    return {"answer": answer}


@traceable(
    run_type="chain",
    name="Build Trainee Assistant Pipeline",
    metadata={"pipeline": "trainee_assistant", "graph_type": "langgraph"}
)
def build_langgraph():
    builder = StateGraph(ChatState)

    builder.add_node("vector_search_node", vector_search_node)
    builder.add_node("generate_answer_node", generate_answer_node)

    builder.set_entry_point("vector_search_node")
    builder.add_edge("vector_search_node", "generate_answer_node")

    return builder.compile()
