# 본 코드는 문제 생성 결과를 JSON Lines (.jsonl) 형태로 저장하는 코드입니다.

import json
import os

from utils.naming import filename_to_collection


# 문제 생성 결과 저장
def save_question_result(
    chunk_info: dict, questions_list: list, output_dir="data/outputs/"
):
    os.makedirs(output_dir, exist_ok=True)
    # 컬렉션명을 정규화하여 파일명 생성
    normalized_project = filename_to_collection(chunk_info["project"])
    file_path = os.path.join(output_dir, f"{normalized_project}.jsonl")

    with open(file_path, "a", encoding="utf-8") as f:
        for question_item in questions_list:
            if not isinstance(question_item, dict):
                print(f"Skipping invalid item (not a dict): {question_item}")
                continue

            # 에러 객체인 경우 처리 (generate_question에서 파싱 실패 시 반환하는 형태)
            if "error" in question_item and "raw_response" in question_item:
                error_info = {
                    "chunk_id": chunk_info.get("chunk_id"),
                    "source": chunk_info.get("source"),
                    "page_info_from_chunk": chunk_info.get(
                        "page"
                    ),  # generate_question 에서도 page_number를 넣지만, 청크 단위의 페이지 정보도 기록
                    "error_message": question_item.get("error"),
                    "raw_llm_response": question_item.get("raw_response"),
                }
                f.write(json.dumps(error_info, ensure_ascii=False) + "\n")
                continue

            # 정상적인 문제 객체인 경우, chunk_info의 일부 내용을 문제 객체에 추가 (선택적)
            # generate_question 에서 이미 document_id, page_number, question_id 등을 추가하므로 중복 최소화
            # 여기서는 청크 레벨의 정보를 추가할 수 있습니다.
            question_to_save = question_item.copy()  # 원본 수정을 피하기 위해 복사
            question_to_save["chunk_id_ref"] = chunk_info.get("chunk_id")
            # question_to_save["original_source_text_from_chunk"] = chunk_info.get("source_text") # 매우 길 수 있으므로 주의

            # 각 문제 객체를 JSON 문자열로 변환하여 파일에 한 줄씩 쓰기
            # ensure_ascii=False 옵션으로 한글이 유니코드 이스케이프 없이 저장되도록 함
            f.write(json.dumps(question_to_save, ensure_ascii=False) + "\n")
