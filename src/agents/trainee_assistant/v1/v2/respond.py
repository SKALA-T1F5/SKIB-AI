# agents/respond.py


from fastapi.responses import StreamingResponse
from konlpy.tag import Okt
from openai import AsyncOpenAI

from api.trainee_assistant.schemas.trainee_assistant import QuestionPayload
from config.settings import settings
from db.redisDB.session_manager import append_message, load_message_history
from db.vectorDB.chromaDB.search import ChromaDBSearcher
from src.agents.trainee_assistant.v1.v2.vector_search import (
    build_prompt_from_docs,
    search_chromadb,
)

openai_client = AsyncOpenAI(api_key=settings.api_key)


import logging

logger = logging.getLogger(__name__)


async def generate_answer(payload: QuestionPayload):
    user_id = payload.userId
    user_question = payload.question
    document_id = payload.documentId

    logger.info(
        f"🔍 [질문 수신] user_id: {user_id}, question: {user_question}, document_id: {document_id}"
    )

    # 1. Redis 히스토리 로드
    history = await load_message_history(user_id)
    logger.debug(f"📚 [불러온 이전 히스토리] {history}")
    history.append({"role": "user", "content": user_question})

    # 2. ChromaDB에서 문서 검색
    logger.info(f"🧠 [ChromaDB 검색 시작] collection={document_id}")
    chroma_searcher = ChromaDBSearcher()
    # 1. 사용자 질문에서 키워드 추출
    keywords = extract_keywords(user_question)
    logger.info(f"🔑 [질문 키워드 추출] {keywords}")

    # 2. ChromaDB에서 검색 (전체 유사한 문서 가져오기)
    docs = chroma_searcher.search_similar(
        query=user_question, collection_name=document_id
    )

    # 3. 유사도 + 키워드 기반 필터링
    MIN_SIMILARITY = 0.75
    relevant_docs = [
        doc
        for doc in docs
        if doc["similarity"] >= MIN_SIMILARITY
        and any(k in doc["content"] for k in keywords)
    ]

    if relevant_docs:
        logger.info(f"📄 [관련 문서 있음] {len(relevant_docs)}개")

        # 👉 문서 내용을 context로 명시적으로 추가
        context_prompt = build_prompt_from_docs(user_question, relevant_docs)
        context_role = {"role": "user", "content": context_prompt}

    else:
        logger.warning(
            f"❌ [문서 유사도 부족] 관련 내용을 찾지 못함 (document_id: {document_id})"
        )
        # 👉 유사 문서가 아예 없을 경우, 일반 질문으로 대체
        context_prompt = (
            "⚠️ 관련 문서를 찾을 수 없어 일반적인 답변을 제공합니다.\n\n"
            f"[사용자 질문]\n{user_question}"
        )
        context_role = {"role": "user", "content": context_prompt}

    # 3. GPT 호출
    logger.info("🤖 [GPT 호출 시작]")
    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "당신은 친절한 학습 도우미입니다. "
                    "응답은 3~5문장으로 간결히 작성해주세요."
                ),
            },
            *history,
            context_role,
        ],
    )
    assistant_reply = response.choices[0].message.content
    logger.info("💬 [GPT 응답 수신 완료]")

    # 4. Redis 저장
    await append_message(user_id, "user", user_question)
    await append_message(user_id, "assistant", assistant_reply)
    logger.info("📝 [대화 저장 완료] Redis 세션 저장됨")

    return assistant_reply


async def generate_answer_stream(user_id: str, user_question: str):
    # 1. Redis 대화 불러오기
    history = await load_message_history(user_id)
    history.append({"role": "user", "content": user_question})

    # 2. 문서 기반 context 구성
    docs = await search_chromadb(user_question)
    doc_context = (
        build_prompt_from_docs(user_question, docs)
        if docs
        else f"[사용자 질문]\n{user_question}"
    )

    system_prompt = (
        "당신은 친절하고 유익한 학습 도우미입니다. "
        "답변은 간결하고 핵심적으로 전달해주세요. 최대 3~5문장 이내로 설명하세요."
    )

    # 3. GPT 스트림 응답 요청
    response_stream = await openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": doc_context},
        ],
        stream=True,
    )

    # 4. StreamingResponse로 반환
    async def event_stream():
        full_reply = ""
        async for chunk in response_stream:
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_reply += token
                yield token  # 프론트에 전송

        # 스트리밍 끝나고 Redis 저장
        await append_message(user_id, "user", user_question)
        await append_message(user_id, "assistant", full_reply)

    return StreamingResponse(event_stream(), media_type="text/plain")


def extract_keywords(text: str, top_k: int = 5) -> list[str]:
    """
    사용자 질문에서 명사 및 의미 있는 단어 추출
    """
    okt = Okt()
    words = [
        word
        for word, pos in okt.pos(text)
        if pos in ["Noun", "Alpha", "Verb"] and len(word) > 1
    ]

    # 단순 빈도 기준으로 상위 키워드 선택
    from collections import Counter

    most_common = Counter(words).most_common(top_k)
    return [word for word, _ in most_common]
