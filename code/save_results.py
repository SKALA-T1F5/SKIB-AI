# 본 코드는 문제 생성 결과를 csv 형태로 저장하는 코드입니다.

import csv
import os


# 문제 생성 결과 저장
def save_question_result(chunk: dict, question_data: dict, output_dir="data/outputs/"):
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, f"questions_{chunk['project']}.csv")
    is_new = not os.path.exists(file_path)

    with open(file_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["chunk_id", "chunk_type", "source_text", "question"]
        )
        if is_new:
            writer.writeheader()
        writer.writerow(
            {
                "chunk_id": chunk["chunk_id"],
                "chunk_type": chunk["chunk_type"],
                "source_text": chunk["source_text"],
                "question": question_data["raw"],
            }
        )
