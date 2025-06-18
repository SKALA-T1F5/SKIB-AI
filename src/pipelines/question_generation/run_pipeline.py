"""
문제 생성 파이프라인
텍스트/이미지 블록으로 분해하고 GPT-4o Vision을 사용한 자동 문제 생성 파이프라인

주요 기능:
- PDF 문서 파싱 및 블록 분해 
- Vision API 메시지 포맷 변환
- 벡터 임베딩 생성
- GPT-4o Vision 기반 질문 생성
- 질문과 메타데이터 저장

최종적으로는 PDF 한 개에 대해 문항 자동 생성 파이프라인을 수행합니다.
"""

from src.agents.document_analyzer.tools.unified_parser import parse_pdf_unified
from src.agents.question_generator.tools.question_generator import QuestionGenerator
from utils.change_name import normalize_collection_name
from sentence_transformers import SentenceTransformer
import os
import sys
import time

# 임베딩 모델 로딩 (bge 모델 사용)
embedding_model = SentenceTransformer("BAAI/bge-base-en")

def run_question_generation_pipeline(pdf_path: str, num_objective: int = 3, num_subjective: int = 3):
    """
    문제 생성 파이프라인 실행
    
    Args:
        pdf_path: PDF 파일 경로 (문자열 또는 정수 인덱스)
        num_objective: 생성할 객관식 문제 수
        num_subjective: 생성할 주관식 문제 수
        
    Returns:
        List[Dict]: 생성된 문제들의 리스트
    """
    # PDF 파일 경로 설정 (기존 호환성 유지)
    if isinstance(pdf_path, int):
        if pdf_path == 1:
            pdf_path = "data/raw_docs/2.연말정산시스템(YETA) 매뉴얼.pdf"
        elif pdf_path == 2:
            pdf_path = "data/raw_docs/2_AGS Trouble shooting 가이드_v1.1.pdf"
        elif pdf_path == 3:
            pdf_path = "data/raw_docs/alopex_UI_1.1.2_개발가이드.pdf"
        elif pdf_path == 4:
            pdf_path = "data/raw_docs/To-Be 재무Portal_Process 정의서_FP-07_탄소배출권_v1.0.pdf"
        elif pdf_path == 5:
            pdf_path = "data/raw_docs/Process 흐름도_sample_250527.pdf"
        else:
            raise ValueError(f"지원되지 않는 PDF 인덱스: {pdf_path}")
    
    print(f"🚀 문제 생성 파이프라인 시작")
    print(f"📄 처리할 파일: {pdf_path}")
    print(f"🎯 목표: 객관식 {num_objective}개, 주관식 {num_subjective}개")
    print("=" * 80)
    
    if not os.path.exists(pdf_path):
        print(f"❌ 파일을 찾을 수 없습니다: {pdf_path}")
        return []
    
    filename = os.path.splitext(os.path.basename(pdf_path))[0]
    collection_name = normalize_collection_name(filename)
    
    # 1. PDF를 Docling 스타일 블록으로 변환 (페이지 정보 포함)
    print("📄 1단계: PDF 파싱 및 블록 분해")
    blocks = parse_pdf_unified(pdf_path)
    print(f"✅ {len(blocks)}개 블록 추출 완료")

    # 2. QuestionGenerator를 사용하여 블록을 Vision 청크로 변환
    print("🔄 2단계: Vision API 메시지 변환")
    generator = QuestionGenerator()
    processed_vision_chunks = generator._blocks_to_vision_chunks(blocks)
    n_chunks = len(processed_vision_chunks)
    print(f"✅ {n_chunks}개 Vision 청크 생성 완료")

    # 청크가 없는 경우 에러 처리
    if n_chunks == 0:
        print("❌ 처리 가능한 청크가 생성되지 않았습니다.")
        print("💡 문서 형식이나 내용을 확인해주세요.")
        return []

    source_file_name = os.path.basename(pdf_path)

    # 문제 수 분배 계산
    def distribute(total, n):
        if n == 0:
            return []
        base = total // n
        remainder = total % n
        return [base + 1 if i < remainder else base for i in range(n)]

    obj_per_chunk = distribute(num_objective, n_chunks)
    subj_per_chunk = distribute(num_subjective, n_chunks)
    
    print(f"📊 청크별 문제 분배:")
    print(f"   객관식: {obj_per_chunk}")
    print(f"   주관식: {subj_per_chunk}")

    results = []
    objective_count = 0
    subjective_count = 0

    # 3. 각 processed_vision_chunk에 대해 질문 생성 및 저장 반복
    print("\n🤖 3단계: GPT-4o Vision 문제 생성")
    for i, vision_data in enumerate(processed_vision_chunks):
        if objective_count >= num_objective and subjective_count >= num_subjective:
            break
            
        print(f"  📝 청크 {i+1}/{n_chunks} 처리 중...")
        
        messages_for_api = vision_data['messages']
        chunk_metadata = vision_data['metadata']

        # chunk_obj 구성 시, processed_vision_chunks에서 반환된 메타데이터 활용
        page_numbers = chunk_metadata.get("pages", [])
        page_info_for_chunk = str(page_numbers[0]) if page_numbers else "N/A"
        
        section_titles = chunk_metadata.get("sections", [])
        section_info_for_chunk = ", ".join(section_titles) if section_titles else ""

        # 청크 메타데이터 객체 구성 (save_question_result 및 DB 업로드용)
        chunk_obj_for_saving = {
            "chunk_id": f"{collection_name}_vision_c{i}",
            "chunk_type": "vision_processed_chunk",
            "section_title": section_info_for_chunk,
            "source_text": chunk_metadata.get("source_text_combined", ""),
            "project": collection_name,
            "source": source_file_name,
            "page": page_info_for_chunk,
        }

        # 벡터 임베딩은 source_text_combined 전체에 대해 수행할 수 있음
        if chunk_obj_for_saving["source_text"]:
            vector = embedding_model.encode(chunk_obj_for_saving["source_text"]).tolist()
            # upload_chunk_to_collection(chunk_obj_for_saving, vector, collection_name) # 필요시 DB 업로드
        else:
            vector = []

        # 각 chunk별로 할당된 개수만큼만 요청
        num_obj = obj_per_chunk[i]
        num_subj = subj_per_chunk[i]

        if num_obj == 0 and num_subj == 0:
            print(f"    ⏭️ 청크 {i+1}: 할당된 문제 없음, 건너뛰기")
            continue

        print(f"    🎯 청크 {i+1}: 객관식 {num_obj}개, 주관식 {num_subj}개 생성 요청")

        try:
            # GPT-4o Vision API를 통해 질문 생성
            generator = QuestionGenerator()
            questions_list = generator._generate_question(
                messages=messages_for_api, 
                source=source_file_name, 
                page=page_info_for_chunk,
                num_objective=num_obj,
                num_subjective=num_subj,
            )
            
            print(f"    ✅ 청크 {i+1}: {len(questions_list)}개 문제 생성 완료")
            
            # 결과 처리 및 카운트 업데이트
            for question_data in questions_list:
                q_type = question_data["type"]
                if q_type == "OBJECTIVE" and objective_count >= num_objective:
                    continue
                if q_type == "SUBJECTIVE" and subjective_count >= num_subjective:
                    continue

                if q_type == "OBJECTIVE":
                    objective_count += 1
                elif q_type == "SUBJECTIVE":
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
                    "grading_criteria": question_data.get("grading_criteria")
                }

                results.append(result)

            # 생성된 문항과 메타데이터 저장
            save_question_result(chunk_info=chunk_obj_for_saving, questions_list=questions_list)
            
        except Exception as e:
            print(f"    ❌ 청크 {i+1} 문제 생성 실패: {e}")
        
        # API 호출 간 지연 시간 유지
        time.sleep(1)

    print(f"\n🎉 문제 생성 파이프라인 완료!")
    print(f"📊 최종 결과:")
    print(f"   - 총 문제: {len(results)}개")
    print(f"   - 객관식: {objective_count}개 (목표: {num_objective}개)")
    print(f"   - 주관식: {subjective_count}개 (목표: {num_subjective}개)")
    print(f"   - 컬렉션: {collection_name}")
    
    return results


# 하위 호환성을 위한 기존 함수명 유지
def run_pipeline(pdf_path, num_objective: int = 3, num_subjective: int = 3):
    """하위 호환성을 위한 래퍼 함수"""
    return run_question_generation_pipeline(pdf_path, num_objective, num_subjective)


# 터미널에서 직접 실행하는 경우
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python -m src.pipelines.question_generation.run_pipeline <pdf_path> [num_objective] [num_subjective]")
        print()
        print("예시:")
        print("  python -m src.pipelines.question_generation.run_pipeline 'data/raw_docs/sample.pdf' 5 3")
        print("  python -m src.pipelines.question_generation.run_pipeline 1  # 사전 정의된 파일 사용")
        sys.exit(1)

    pdf_path = sys.argv[1]
    
    # 숫자인 경우 정수로 변환
    try:
        pdf_path = int(pdf_path)
    except ValueError:
        pass  # 문자열 경로 그대로 사용
    
    num_objective = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    num_subjective = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    
    run_question_generation_pipeline(pdf_path, num_objective, num_subjective)