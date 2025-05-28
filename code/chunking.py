from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document


def block_to_documents(blocks: list) -> list:
    """
    Docling 블록 리스트를 LangChain Document 객체 리스트로 변환
    """
    docs = []  # 변환된 Document 객체들을 저장할 리스트
    # 블록의 타입이 'paragraph'인 경우에만 처리
    for i, block in enumerate(blocks):
        if block["type"] == "paragraph":
            docs.append(
                Document(
                    page_content=block["content"],
                    # 블록의 타입 정보를 메타데이터로 저장(블록마다 고유 ID 부여 (예: p0, p1, ...))
                    metadata={"chunk_type": "paragraph", "chunk_id": f"p{i}"},
                )
            )
        # 향후 table, list 등 확장 가능
    return docs


def split_docs(docs: list, chunk_size=500, chunk_overlap=50) -> list:
    """
    LangChain Document 객체들을 지정된 토큰 크기로 분할
    """
    # Recursive 방식으로 텍스트를 분할하는 TextSplitter 생성
    splitter = RecursiveCharacterTextSplitter(
        # 청크 하나당 최대 토큰 수, 인접 청크 간 겹치는 토큰 수
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return splitter.split_documents(docs)  # 문서 분할 수행 후 결과 반환
