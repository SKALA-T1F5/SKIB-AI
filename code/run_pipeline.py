"""
텍스트/이미지 블록으로 분해하고 (parse_pdf_to_docling_blocks)
LangChain Document로 변환 및 분할 (block_to_documents, split_docs)
GPT-4o Vision 메시지 포맷으로 변환 (docling_blocks_to_vision_messages)
각 청크에 대해:
- 벡터 임베딩 생성 (SentenceTransformer)
- Vision 기반 질문 생성 (generate_question)
- 질문과 메타데이터 저장 (save_question_result)
최종적으로는 PDF 한 개에 대해 문항 자동 생성 파이프라인을 수행합니다.
"""

from code.docling_parser import parse_pdf_to_docling_blocks
from code.chunking import block_to_documents, split_docs
from code.generate_questions import generate_question
from code.save_results import save_question_result
from code.preprocess_docling import docling_blocks_to_vision_messages
from code.change_name import normalize_collection_name
from sentence_transformers import SentenceTransformer
import os
import sys

# 임베딩 모델 로딩 (bge 모델 사용)
embedding_model = SentenceTransformer("BAAI/bge-base-en")


def run_pipeline(pdf_path: str, collection_name: str):
    # 1. PDF를 Docling 스타일 블록으로 변환
    blocks = parse_pdf_to_docling_blocks(pdf_path)

    # 2. 블록을 LangChain 문서 객체로 변환
    docs = block_to_documents(blocks)

    # 3. 문서를 지정된 크기로 분할 (500자 단위, 50자 겹침)
    chunks = split_docs(docs)

    # 4. Vision 입력 형식 (텍스트+이미지)으로 변환
    vision_chunks = docling_blocks_to_vision_messages(blocks)

    # 5. 각 청크에 대해 질문 생성 및 저장 반복
    for i, (doc, messages) in enumerate(zip(chunks, vision_chunks)):
        page = doc.metadata.get("page", "N/A")  # 페이지 정보
        source = os.path.basename(pdf_path)  # 파일명 (출처 표시용)

        # 청크 메타데이터 객체 구성
        chunk_obj = {
            "chunk_id": f"{collection_name}_c{i}",
            "chunk_type": doc.metadata.get("chunk_type", "unknown"),
            "section_title": doc.metadata.get("section_title", ""),
            "source_text": doc.page_content,
            "project": collection_name,
            "source": source,
            "page": page,  # 페이지 정보 포함
        }

        # 문서 내용 벡터 임베딩 (추후 DB 업로드용)
        vector = embedding_model.encode(doc.page_content).tolist()
        # upload_chunk_to_collection(chunk_obj, vector, collection_name)

        # GPT-4o Vision API를 통해 질문 생성
        question_data = generate_question(messages, source=source, page=page)
        # 생성된 문항과 메타데이터 저장
        save_question_result(chunk_obj, question_data)

    print(f"✅ 문서 '{collection_name}' 문제 생성 완료")


# 터미널에서 직접 실행하는 경우
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m code.run_pipeline <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    filename = os.path.splitext(os.path.basename(pdf_path))[0]
    collection_name = normalize_collection_name(filename)
    run_pipeline(pdf_path, collection_name)
