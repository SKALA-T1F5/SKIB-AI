#!/usr/bin/env python3
"""
통합 파서로 처리한 결과를 VectorDB에 업로드하는 스크립트

사용법:
python upload_to_vectordb.py "data/raw_docs/자동차 리포트.pdf"
"""

import os
import sys

from sentence_transformers import SentenceTransformer

from src.agents.document_analyzer.tools.unified_parser import parse_pdf_unified
from utils.naming import filename_to_collection

from .weaviate_utils import upload_chunk_to_collection

# 임베딩 모델 로딩
embedding_model = SentenceTransformer("BAAI/bge-base-en")


def upload_document_to_vectordb(pdf_path: str):
    """PDF 문서를 파싱하고 VectorDB에 업로드"""
    print(f"📄 문서 처리 중: {pdf_path}")

    # 1. 통합 파서로 처리
    source_file = os.path.basename(pdf_path)
    # 파일명을 정규화하여 컬렉션명 생성
    base_name = os.path.splitext(source_file)[0]
    collection_name = filename_to_collection(base_name)

    print(f"🏷️ 컬렉션명: {collection_name}")

    blocks = parse_pdf_unified(pdf_path, collection_name)

    # 2. 블록 타입 확인
    print(f"📊 전체 블록 수: {len(blocks)}")
    for block_type in set(b.get("type", "unknown") for b in blocks):
        count = len([b for b in blocks if b.get("type") == block_type])
        print(f"   - {block_type}: {count}개")

    # 텍스트 블록만 추출 (표와 이미지는 메타데이터로만 활용)
    text_blocks = []
    for b in blocks:
        text_content = (
            b.get("text", "") or b.get("content", "") or b.get("source_text", "")
        )
        if text_content and text_content.strip():
            text_blocks.append(b)

    print(f"📝 업로드할 텍스트 블록: {len(text_blocks)}개")

    # 3. 각 블록을 VectorDB에 업로드
    uploaded_count = 0

    for i, block in enumerate(text_blocks):
        # 여러 텍스트 필드 확인
        text_content = (
            block.get("text", "")
            or block.get("content", "")
            or block.get("source_text", "")
        ).strip()

        if not text_content:
            continue

        # 청크 메타데이터 구성
        chunk_obj = {
            "chunk_id": f"{collection_name}_block_{i}",
            "chunk_type": block.get("type", "paragraph"),
            "section_title": block.get("section_title", ""),
            "source_text": text_content,
            "project": collection_name,
            "source": source_file,
        }

        try:
            # 벡터 임베딩 생성
            vector = embedding_model.encode(text_content).tolist()

            # VectorDB에 업로드
            upload_chunk_to_collection(chunk_obj, vector, collection_name)
            uploaded_count += 1

        except Exception as e:
            print(f"⚠️ 블록 {i} 업로드 실패: {e}")

    print(f"✅ 업로드 완료: {uploaded_count}개 블록")
    return uploaded_count


def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법: python upload_to_vectordb.py <pdf_path>")
        print("예시: python upload_to_vectordb.py 'data/raw_docs/자동차 리포트.pdf'")
        sys.exit(1)

    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"❌ 파일을 찾을 수 없습니다: {pdf_path}")
        sys.exit(1)

    print("🚀 VectorDB 업로드 시작")
    print("=" * 50)

    try:
        upload_document_to_vectordb(pdf_path)
        print("\n🎉 VectorDB 업로드 완료!")
        print("\n💡 확인 방법:")
        print("   python db/vectorDB/check_vectordb.py")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
