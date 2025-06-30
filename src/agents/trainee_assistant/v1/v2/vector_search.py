from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma

from config.settings import settings

# 공통 임베딩 함수 정의
embedding_fn = OpenAIEmbeddings(api_key=settings.api_key)


def get_chroma_by_collection(collection_name: str) -> Chroma:
    return Chroma(
        collection_name=collection_name,
        persist_directory=settings.CHROMA_DIR,
        embedding_function=embedding_fn,
    )


async def search_chromadb(query: str, collection_name: str, top_k: int = 3):
    chroma = get_chroma_by_collection(collection_name)
    docs = chroma.similarity_search(query, k=top_k)
    return docs


def build_prompt_from_docs(user_question: str, docs: list) -> str:
    context_str = "\n\n".join([doc["content"] for doc in docs])
    return f"""[📚 참고 문서 내용 (자동 검색)]\n{context_str}\n\n[🧑 사용자 질문]\n{user_question}\n\n✍️ 위 문서 내용에 기반하여 답변하세요. 반드시 문서 내용을 인용해 응답하세요."""
