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

from typing import List, Dict
from agents.question_generator.docling_parser import parse_pdf_to_docling_blocks
from agents.question_generator.chunking import block_to_documents, split_docs
from agents.question_generator.generate_questions import generate_question
from agents.question_generator.save_results import save_question_result
from agents.question_generator.preprocess_docling import docling_blocks_to_vision_messages
from agents.question_generator.change_name import normalize_collection_name
from sentence_transformers import SentenceTransformer
import os
from datetime import datetime

embedding_model = SentenceTransformer("BAAI/bge-base-en")


def run_pipeline(pdf_path: str, num_objective: int, num_subjective: int) -> List[Dict]:
    collection_name = normalize_collection_name(os.path.splitext(os.path.basename(pdf_path))[0])
    blocks = parse_pdf_to_docling_blocks(pdf_path)
    docs = block_to_documents(blocks)
    chunks = split_docs(docs)
    vision_chunks = docling_blocks_to_vision_messages(blocks)

    results = []
    objective_count = 0
    subjective_count = 0

    for i, (doc, messages) in enumerate(zip(chunks, vision_chunks)):
        # 중복 제거 생략, 실제에선 UUID 등 추천
        page = doc.metadata.get("page", "N/A")
        source = os.path.basename(pdf_path)

        chunk_obj = {
            "chunk_id": f"{collection_name}_c{i}",
            "chunk_type": doc.metadata.get("chunk_type", "unknown"),
            "section_title": doc.metadata.get("section_title", ""),
            "source_text": doc.page_content,
            "project": collection_name,
            "source": source,
            "page": page,
        }

        vector = embedding_model.encode(doc.page_content).tolist()

                # GPT 기반 질문 생성 → 여러 개 리스트로 반환됨
        generated_questions = generate_question(
            messages,
            source=source,
            page=page,
            num_objective=num_objective,
            num_subjective=num_subjective,
            difficulty=3,
        )

        print(generated_questions)

        for question_data in generated_questions:
            q_type = question_data["type"]
            if q_type == "multiple_choice":
                if objective_count >= num_objective:
                    continue
                objective_count += 1
            else:
                if subjective_count >= num_subjective:
                    continue
                subjective_count += 1

            # created_at, key 제거하고 그대로 반환
            result = {
                "type": question_data["type"],
                "difficulty_level": question_data["difficulty_level"],
                "question": question_data["question"],
                "options": question_data.get("options"),
                "answer": question_data["answer"],
                "explanation": question_data.get("explanation"),
                "document_id": collection_name,
                "tags": question_data.get("tags", []),
            }

            results.append(result)

        # 둘 다 생성 완료 시 종료
        if objective_count >= num_objective and subjective_count >= num_subjective:
            break

    return results


if __name__ == "__main__":
    import sys
    from pprint import pprint
    from agents.question_generator.change_name import normalize_collection_name

    if len(sys.argv) != 4:
        print("Usage: python -m agents.question_generator.run_pipeline <pdf_path> <objective_count> <subjective_count>")
        sys.exit(1)

    # 인자: PDF 경로, 객관식 수, 주관식 수
    pdf_path = sys.argv[1]
    num_objective = int(sys.argv[2])
    num_subjective = int(sys.argv[3])


    # 파이프라인 실행
    result = run_pipeline(
        pdf_path=pdf_path,
        num_objective=num_objective,
        num_subjective=num_subjective
    )

    # 결과 출력
    print(f"\n✅ 생성된 문제 총 {len(result)}개:")
    pprint(result, sort_dicts=False)
