"""
Docling 형식의 블록을 GPT-4 Vision 모델이 이해할 수 있는 text-image 메시지 포맷으로 변환합니다.
각 블록 타입(텍스트, 이미지, 표, 리스트, 섹션)에 대해 적절한 변환을 수행합니다.
"""

import base64
import os
from typing import List, Dict
import json

# 이미지 저장 디렉토리 (docling_parser.py와 일관성 유지)
# docling_parser.py에서 이미지를 저장한 경로를 참조하기 위함.
IMAGE_SOURCE_DIR = "data/images" 

def docling_blocks_to_vision_messages(blocks: List[Dict]) -> List[Dict]:
    """
    Docling 블록(paragraph, image, section)을 GPT-4 Vision 메시지로 변환하고,
    각 청크에 대한 메타데이터를 포함합니다.
    청킹은 주로 section 변경 시 또는 MAX_CHUNK_LENGTH 도달 시 발생합니다.
    
    Args:
        blocks (List[Dict]): 'paragraph', 'image', 'section' 타입의 블록 리스트.
                             각 블록은 content/path/title 과 metadata({'page': int})를 가짐.
        
    Returns:
        List[Dict]: 각 요소는 {'messages': List[Dict], 'metadata': Dict} 형태의 딕셔너리.
    """
    output_chunks_with_metadata = []
    current_chunk_messages = []
    current_chunk_metadata = {
        "pages": set(),
        "sections": set(), # 현재 청크에 포함된 섹션 제목들
        "source_texts": [] # 현재 청크를 구성한 원본 텍스트/정보들
    }
    current_chunk_length = 0
    # MAX_CHUNK_LENGTH는 API 토큰 제한 및 원하는 컨텍스트 크기에 따라 조절 가능
    MAX_CHUNK_LENGTH = 20000 # 예: 이전과 동일하게 유지 또는 필요시 조절
    
    # save_current_chunk 함수는 이전과 거의 동일하게 유지, sections 메타데이터 추가
    def save_current_chunk():
        nonlocal current_chunk_messages, current_chunk_metadata, current_chunk_length
        if current_chunk_messages:
            final_metadata = {
                "pages": sorted(list(current_chunk_metadata["pages"])),
                "sections": sorted(list(current_chunk_metadata["sections"])),
                "source_text_combined": "\n".join(current_chunk_metadata["source_texts"])
            }
            output_chunks_with_metadata.append({
                "messages": current_chunk_messages,
                "metadata": final_metadata
            })
        current_chunk_messages = []
        current_chunk_metadata = {"pages": set(), "sections": set(), "source_texts": []}
        current_chunk_length = 0

    for block_idx, block in enumerate(blocks):
        block_type = block.get("type")
        page_no = block.get("metadata", {}).get("page")

        if page_no is not None:
            current_chunk_metadata["pages"].add(page_no)
        else:
            print(f"Warning: Block (type: {block_type}) at index {block_idx} has no page number.")
            # 페이지 번호가 없는 블록은 일단 현재 청크에 포함시키되, 로그를 남김.
            # 또는 여기서 continue 하여 건너뛸 수도 있음.

        block_text_representation = "" # 길이 계산 및 source_texts 추가용

        if block_type == "section":
            # 섹션 블록을 만나면, 이전까지의 청크를 저장하고 새 청크 시작
            if current_chunk_messages: # 이전 청크에 내용이 있을 경우에만 저장
                # print(f"New section encountered. Saving previous chunk.")
                save_current_chunk()
                # 새 청크 시작 시 현재 블록(섹션)의 페이지 번호 반영
                if page_no is not None: current_chunk_metadata["pages"].add(page_no)
            
            title = block.get("title", "Untitled Section")
            current_chunk_metadata["sections"].add(title) # 메타데이터에 섹션 제목 추가
            section_header_text = f"## {title}"
            block_text_representation = section_header_text
            
            # 메시지 추가 전 길이 확인 (섹션 제목 자체가 너무 길 경우)
            if current_chunk_length + len(section_header_text) > MAX_CHUNK_LENGTH and current_chunk_messages:
                save_current_chunk()
                if page_no is not None: current_chunk_metadata["pages"].add(page_no)
                current_chunk_metadata["sections"].add(title) # 새 청크에도 섹션 반영
            
            current_chunk_messages.append({"type": "text", "text": section_header_text})
            current_chunk_length += len(section_header_text)
            current_chunk_metadata["source_texts"].append(f"[Section Title: {title} on page {page_no or 'N/A'}]")

        elif block_type == "paragraph":
            text_content = block.get("content", "")
            if not isinstance(text_content, str):
                text_content = str(text_content)
            block_text_representation = text_content
            current_chunk_metadata["source_texts"].append(text_content) # 원본 텍스트 기록
            
            # 텍스트를 MAX_CHUNK_LENGTH에 맞춰 분할 추가
            start_idx = 0
            while start_idx < len(text_content):
                if current_chunk_length >= MAX_CHUNK_LENGTH and current_chunk_messages:
                    save_current_chunk()
                    if page_no is not None: current_chunk_metadata["pages"].add(page_no)
                    # 현재 단락이 여러 청크에 걸쳐 나눠질 경우, 해당 청크들에도 현재 섹션 정보를 유지하고 싶다면,
                    # current_chunk_metadata["sections"]를 save_current_chunk 후 비우지 않거나, 다시 추가해야 함.
                    # 여기서는 save_current_chunk에서 sections도 비우므로, 필요시 이전 섹션 정보를 다시 참조하여 추가.
                    # (단순화를 위해, 여기서는 새 청크의 sections는 해당 청크에서 처음 등장하는 section 블록으로만 채워짐)

                remaining_space = MAX_CHUNK_LENGTH - current_chunk_length
                part_to_add = text_content[start_idx : start_idx + remaining_space]
                
                current_chunk_messages.append({"type": "text", "text": part_to_add})
                current_chunk_length += len(part_to_add)
                start_idx += len(part_to_add)

                if current_chunk_length >= MAX_CHUNK_LENGTH and current_chunk_messages:
                    save_current_chunk()
                    if page_no is not None: current_chunk_metadata["pages"].add(page_no)

        elif block_type == "image":
            image_filename = block.get("path")
            if not image_filename:
                print(f"Warning: Image block on page {page_no or 'N/A'} has no path. Skipping.")
                continue

            image_path = os.path.join(IMAGE_SOURCE_DIR, image_filename)
            block_text_representation = f"[Image: {image_filename} on page {page_no or 'N/A'}]"
            current_chunk_metadata["source_texts"].append(block_text_representation)

            if os.path.exists(image_path):
                try:
                    with open(image_path, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode("utf-8")
                    
                    # 이미지 추가 전 길이 확인 (이미지는 토큰 비용이 크므로, 너무 긴 청크에 추가 X)
                    if current_chunk_length > MAX_CHUNK_LENGTH * 0.9 and current_chunk_messages:
                        save_current_chunk()
                        if page_no is not None: current_chunk_metadata["pages"].add(page_no)

                    current_chunk_messages.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded}"}
                    })
                    # 이미지 자체는 current_chunk_length에 직접 더하지 않음
                except Exception as e:
                    print(f"Error processing image {image_path} on page {page_no or 'N/A'}: {e}")
            else:
                print(f"Warning: Image file not found at {image_path}. Skipping image content.")
        
        else:
            # 알 수 없는 블록 타입 또는 Docling 파서에서 건너뛰기로 한 Table/List 등
            print(f"Info: Skipping block type '{block_type}' on page {page_no or 'N/A'} or it was not processed by parser.")
            original_content = block.get("content")
            if original_content:
                 block_text_representation = str(original_content) if not isinstance(original_content, (dict, list)) else json.dumps(original_content)
                 current_chunk_metadata["source_texts"].append(f"[Skipped Block: {block_type} on page {page_no or 'N/A'} - Content: {block_text_representation[:100]}...]")
            else:
                 current_chunk_metadata["source_texts"].append(f"[Skipped Block: {block_type} on page {page_no or 'N/A'}]")

        # 블록 처리 후 현재 청크 길이가 너무 길면 저장 (주로 paragraph의 긴 텍스트 때문)
        if current_chunk_length >= MAX_CHUNK_LENGTH and current_chunk_messages:
            # print(f"Chunk full after processing block type {block_type}. Saving.")
            save_current_chunk()
            # 새 청크를 위해 현재 블록의 페이지/섹션 정보 다시 추가 필요할 수 있음
            if page_no is not None: current_chunk_metadata["pages"].add(page_no)
            if block_type == "section" and "title" in block: # 현재 블록이 섹션이면 새 청크에도 섹션 정보 추가
                 current_chunk_metadata["sections"].add(block["title"])

    # 마지막 남은 청크 저장
    save_current_chunk()

    print(f"Total chunks with metadata created: {len(output_chunks_with_metadata)}")
    return output_chunks_with_metadata


def _format_table_for_vision(table_content: Dict) -> str:
    """
    표 데이터를 마크다운 형식의 문자열로 변환합니다.
    'table_content'는 {'headers': [...], 'data': [[...], [...]]} 형태를 기대합니다.
    """
    # content가 예상한 dict 형태가 아니거나, 필요한 키가 없을 경우를 대비
    if not isinstance(table_content, dict) or "data" not in table_content:
        print(f"Warning: Invalid table_content for _format_table_for_vision: {table_content}")
        return "" 
    
    data = table_content.get("data", [])
    headers = table_content.get("headers", []) # headers가 없을 수도 있음을 고려

    if not data and not headers: # 데이터도 헤더도 없으면 빈 문자열 반환
        return ""

    table_str = ""
    # 헤더 행 생성 (헤더가 있는 경우)
    if headers:
        table_str += "| " + " | ".join(str(h) for h in headers) + " |\\n"
        table_str += "|" + " |".join([":---:" if i < len(headers) else "---" for i in range(len(headers))]) + "|\\n" # 정렬 추가 및 길이 맞춤
    elif data and data[0]: # 헤더가 없고 데이터가 있으면, 첫 행 길이에 맞춰 구분선 생성
        num_cols = len(data[0])
        table_str += "|" + " |".join([":---:"] * num_cols) + "|\\n"


    # 데이터 행 추가
    for row in data:
        # 각 셀의 내용이 문자열이 아닐 수도 있으므로 str()로 변환
        table_str += "| " + " | ".join(str(cell) for cell in row) + " |\\n"
    
    return table_str.strip() # 마지막 줄바꿈 제거


def _format_list_for_vision(list_items: List[str]) -> str:
    """
    리스트 아이템을 마크다운 형식의 문자열로 변환합니다.
    'list_items'는 문자열의 리스트를 기대합니다.
    """
    if not isinstance(list_items, list): # 리스트가 아니면 빈 문자열
        print(f"Warning: Invalid list_items for _format_list_for_vision: {list_items}")
        return ""
    
    # 각 아이템이 문자열인지 확인하고, 아니면 str()로 변환
    return "\\n".join(f"- {str(item)}" for item in list_items).strip() # 마지막 줄바꿈 제거
