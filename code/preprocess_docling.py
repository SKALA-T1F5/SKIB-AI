# 코드 설명 : Docling 형식의 블록 리스트(paragraph, image, section 등)를 GPT-4o Vision 모델이 이해할 수 있는 text-image 메시지 포맷으로 변환
# 이미지는 base64로 인코딩되며, 문단과 섹션 헤더는 텍스트로 구성됨
# 섹션(section)을 기준으로 하나의 메시지 청크 단위(chunk)를 나눔


import base64
import os
from typing import List, Dict


# 블록 단위로 GPT Vision 메시지 구성
# combo = paragraph + image + paragraph ...
def docling_blocks_to_vision_messages(
    blocks: List[Dict], image_dir="data/images"
) -> List[List[Dict]]:
    chunks = []
    current_chunk = []

    for block in blocks:
        # 문단 블록: text 타입 메시지로 추가
        if block["type"] == "paragraph":
            current_chunk.append({"type": "text", "text": block["content"]})

        # 이미지 블록: 파일을 base64로 읽어 image_url 타입 메시지로 추가
        elif block["type"] == "image":
            image_path = os.path.join(image_dir, block["path"])  # 이미지 경로 생성
            if os.path.exists(image_path):  # 파일이 존재할 경우에만 처리
                with open(image_path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode(
                        "utf-8"
                    )  # base64 인코딩
                    current_chunk.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{encoded}"},
                        }
                    )
        # 섹션 블록: 이전 청크를 하나로 묶어 chunks에 추가하고, 새로운 섹션 시작
        elif block["type"] == "section":
            if current_chunk:
                chunks.append(current_chunk)  # 이전 청크 저장
                current_chunk = []  # 새로운 청크 시작

            # 섹션 제목을 markdown 스타일로 삽입
            current_chunk.append({"type": "text", "text": f"## {block['title']}"})

    # 마지막 청크가 남아 있다면 추가
    if current_chunk:
        chunks.append(current_chunk)

    return chunks
