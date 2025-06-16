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

from src.agents.document_analyzer.tools.unified_parser import parse_pdf_unified
from src.agents.question_generator.chunking import block_to_documents, split_docs
from src.agents.question_generator.generate_questions import generate_question
from src.agents.question_generator.save_results import save_question_result
from src.agents.question_generator.preprocess_docling import docling_blocks_to_vision_messages
from utils.change_name import normalize_collection_name
from sentence_transformers import SentenceTransformer
import os
import sys
import time

# 임베딩 모델 로딩 (bge 모델 사용)
embedding_model = SentenceTransformer("BAAI/bge-base-en")

def run_pipeline(pdf_path: int, num_objective: int = 3, num_subjective: int = 3):
    # 0. PDF 파일 경로와 컬렉션 이름 설정
    if pdf_path == 1:
        pdf_path = "/Users/domwis/VSCode/SKIB/SKIB-AI/data/raw_docs/2.연말정산시스템(YETA) 매뉴얼.pdf"
    elif pdf_path == 2:
        pdf_path = "/Users/domwis/VSCode/SKIB/SKIB-AI/data/raw_docs/2_AGS Trouble shooting 가이드_v1.1.pdf"
    elif pdf_path == 3:
        pdf_path = "/Users/domwis/VSCode/SKIB/SKIB-AI/data/raw_docs/alopex_UI_1.1.2_개발가이드.pdf"
    elif pdf_path == 4:
        pdf_path = "/Users/domwis/VSCode/SKIB/SKIB-AI/data/raw_docs/To-Be 재무Portal_Process 정의서_FP-07_탄소배출권_v1.0.pdf"
    filename = os.path.splitext(os.path.basename(pdf_path))[0]
    collection_name = normalize_collection_name(filename)
    # 1. PDF를 Docling 스타일 블록으로 변환 (페이지 정보 포함)
    blocks = parse_pdf_unified(pdf_path)

    # 2. Docling 블록을 Vision API 입력 형식의 메시지 청크와 메타데이터로 변환
    # 이 함수는 이제 각 청크에 대한 메시지 리스트와 메타데이터 딕셔너리를 포함하는 딕셔너리 리스트를 반환합니다.
    # 예: [{'messages': [...], 'metadata': {'pages': [...], 'source_text_combined': "..."}}, ...]
    processed_vision_chunks = docling_blocks_to_vision_messages(blocks)

    # 3. (선택 사항) LangChain 문서 객체 및 고정 크기 청킹 로직은 여기서는 직접 사용하지 않음
    # docs = block_to_documents(blocks) # 필요시 유지 또는 제거
    # chunks_split_docs = split_docs(docs, chunk_size=40, chunk_overlap=10) # 이 부분은 RateLimit의 원인이므로 제거 또는 수정

    source_file_name = os.path.basename(pdf_path)

    processed_vision_chunks = docling_blocks_to_vision_messages(blocks)
    n_chunks = len(processed_vision_chunks)

        # 분배 계산
    def distribute(total, n):
        base = total // n
        remainder = total % n
        return [base + 1 if i < remainder else base for i in range(n)]

    obj_per_chunk = distribute(num_objective, n_chunks)
    subj_per_chunk = distribute(num_subjective, n_chunks)

    results = []
    objective_count = 0
    subjective_count = 0

    # 4. 각 processed_vision_chunk에 대해 질문 생성 및 저장 반복
    for i, vision_data in enumerate(processed_vision_chunks):
        if objective_count >= num_objective and subjective_count >= num_subjective:
            break
        messages_for_api = vision_data['messages']
        chunk_metadata = vision_data['metadata']

        # chunk_obj 구성 시, processed_vision_chunks에서 반환된 메타데이터 활용
        page_numbers = chunk_metadata.get("pages", [])
        # 페이지 번호를 문자열로 변환 (예: "p3, p4-5")하거나 첫 페이지만 사용 등 결정 필요
        page_info_for_chunk = str(page_numbers[0]) if page_numbers else "N/A"
        
        section_titles = chunk_metadata.get("sections", [])
        section_info_for_chunk = ", ".join(section_titles) if section_titles else ""

        # 청크 메타데이터 객체 구성 (save_question_result 및 DB 업로드용)
        chunk_obj_for_saving = {
            "chunk_id": f"{collection_name}_vision_c{i}", # ID 체계 변경 가능
            "chunk_type": "vision_processed_chunk", # 청크 타입 명시
            "section_title": section_info_for_chunk,
            "source_text": chunk_metadata.get("source_text_combined", ""), # 결합된 원본 텍스트
            "project": collection_name,
            "source": source_file_name,
            "page": page_info_for_chunk, # 페이지 정보 사용
        }

        # 벡터 임베딩은 source_text_combined 전체에 대해 수행할 수 있음
        if chunk_obj_for_saving["source_text"]:
            vector = embedding_model.encode(chunk_obj_for_saving["source_text"]).tolist()
            # upload_chunk_to_collection(chunk_obj_for_saving, vector, collection_name) # 필요시 DB 업로드
        else:
            vector = [] # 빈 텍스트의 경우 빈 벡터

        # 각 chunk별로 할당된 개수만큼만 요청
        num_obj = obj_per_chunk[i]
        num_subj = subj_per_chunk[i]

        if num_obj == 0 and num_subj == 0:
            continue

        # GPT-4o Vision API를 통해 질문 생성
        # generate_question 호출 시 source와 page는 chunk_obj_for_saving의 값을 사용
        # num_objective와 num_subjective는 generate_question 함수의 기본값을 사용하거나 여기서 지정할 수 있습니다.
        questions_list = generate_question(
            messages=messages_for_api, 
            source=source_file_name, 
            page=page_info_for_chunk,
            num_objective=num_obj,
            num_subjective=num_subj,
        )
        print(len(questions_list), "questions generated for chunk", i)
        for question_data in questions_list:
            q_type = question_data["type"]
            if q_type == "OBJECTIVE" and objective_count >= num_objective:
                continue
            if q_type != "SUBJECTIVE" and subjective_count >= num_subjective:
                continue

            if q_type == "OBJECTIVE":
                objective_count += 1
            else:
                subjective_count += 1

            result = {
                "type": question_data["type"],
                "difficulty_level": question_data["difficulty_level"],
                "question": question_data["question"],
                "options": question_data.get("options"),
                "answer": question_data["answer"],
                "explanation": question_data.get("explanation"),
                "document_id": 1,  # 문서 ID는 1로 고정 (나중에 실제 문서 ID로 변경 필요)
                "tags": question_data.get("tags", []),
                "grading_criteria": question_data.get("grading_criteria")  # 새 필드 추가
            }

            results.append(result)

        # 생성된 문항과 메타데이터 저장
        # save_question_result는 이제 chunk_info와 questions_list를 받습니다.
        save_question_result(chunk_info=chunk_obj_for_saving, questions_list=questions_list)
        
        time.sleep(1) # API 호출 간 지연 시간 유지

    print(f"✅ 문서 '{collection_name}' 문제 생성 완료: 총 {len(results)}개")
    return results


# 터미널에서 직접 실행하는 경우
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m agents.question_generator.run_pipeline <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    filename = os.path.splitext(os.path.basename(pdf_path))[0]
    collection_name = normalize_collection_name(filename)
    run_pipeline(pdf_path)
