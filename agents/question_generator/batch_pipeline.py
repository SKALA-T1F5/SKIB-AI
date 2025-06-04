# code/batch_pipeline.py
# -----------------------------
import os
from agents.question_generator.run_pipeline import run_pipeline
from agents.question_generator.change_name import normalize_collection_name
from db.vectorDB.weaviate_utils import get_client

RAW_DOCS_DIR = "data/raw_docs"


def run_all_documents():
    pdf_files = [f for f in os.listdir(RAW_DOCS_DIR) if f.endswith(".pdf")]

    # PDF 파일이 하나도 없을 경우 경고 출력 후 함수 종료
    if not pdf_files:
        print("❗ PDF 파일이 없습니다: data/raw_docs/")
        return

    # 각 PDF 파일에 대해 파이프라인 실행
    for filename in pdf_files:
        # 파일의 전체 경로 구성
        pdf_path = os.path.join(RAW_DOCS_DIR, filename)
        # 파일 이름에서 확장자 제거하여 collection 이름 원본 생성
        collection_name_raw = os.path.splitext(filename)[0]
        # collection 이름을 정규화 (예: 소문자 변환, 공백 제거 등 사용자 정의 함수)
        collection_name = normalize_collection_name(collection_name_raw)
        print(
            f"\n🚀 실행 중: {filename} → 컬렉션: '{collection_name}'"
        )  # 실행 로그 출력
        try:
            run_pipeline(
                pdf_path, collection_name
            )  # 해당 PDF 파일을 처리하는 메인 파이프라인 실행
        except Exception as e:
            print(
                f"❌ 오류 발생: {filename} — {e}"
            )  # 처리 중 오류 발생 시 에러 메시지 출력 (파일 이름 포함)

    get_client().close()  # ✅ 모든 문서 처리 후 한 번만 닫기


if __name__ == "__main__":
    run_all_documents()
