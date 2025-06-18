"""
통합 PDF 파서 + GPT-4 Vision 질문 생성
- Docling: 텍스트 구조화 (paragraph, section, heading)
- pdfplumber + PyMuPDF: 표 추출 (감지 + 렌더링)
- PyMuPDF: 이미지 추출 (품질 필터링)
- GPT-4 Vision: 자동 질문 생성
"""

import base64
import os
from typing import Dict, List

import fitz  # PyMuPDF
import pdfplumber

from src.agents.question_generator.tools.question_generator import QuestionGenerator
from utils.change_name import normalize_collection_name

from .image_extractor import _extract_quality_images
from .table_extractor import _extract_tables
from .text_extractor import _extract_structured_text_with_docling


def parse_pdf_unified(
    pdf_path: str,
    collection_name: str = None,
    generate_questions: bool = False,
    num_objective: int = 3,
    num_subjective: int = 3,
) -> List[Dict]:
    """
    통합 PDF 파서: Docling 텍스트 구조화 + 선택적 요소 추출 + GPT-4 Vision 질문 생성

    Args:
        pdf_path: PDF 파일 경로
        collection_name: 컬렉션명
        generate_questions: GPT-4 Vision으로 질문 생성 여부
        num_objective: 객관식 문제 수
        num_subjective: 주관식 문제 수

    Returns:
        List[Dict]: 통합 추출된 블록들 (질문 생성 시 questions 필드 추가)
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    if collection_name:
        normalized_name = normalize_collection_name(collection_name)
        IMAGE_SAVE_DIR = f"data/images/{normalized_name}"
    else:
        IMAGE_SAVE_DIR = "data/images/unified"
    os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)
    print(f"📄 통합 파서로 PDF 처리 중: {pdf_path}")
    # 1. Docling으로 구조화된 텍스트 추출
    print("📝 Docling으로 텍스트 구조 추출 중...")
    text_blocks = _extract_structured_text_with_docling(pdf_path)
    # 2. 선택적 요소 추출 (표, 이미지, 차트)
    print("🎯 선택적 요소 추출 중...")
    visual_blocks = _extract_visual_elements(pdf_path, IMAGE_SAVE_DIR)
    # 3. 결합 및 정렬
    all_blocks = text_blocks + visual_blocks
    # 페이지별로 정렬
    all_blocks.sort(key=lambda x: x.get("metadata", {}).get("page", 0))
    print(f"✅ 통합 파서 완료:")
    print(f"  - 총 블록: {len(all_blocks)}개")
    print(
        f"  - 텍스트 블록: {len([b for b in all_blocks if b.get('type') in ['paragraph', 'section', 'heading']])}개"
    )
    print(f"  - 표: {len([b for b in all_blocks if b.get('type') == 'table'])}개")
    print(f"  - 이미지: {len([b for b in all_blocks if b.get('type') == 'image'])}개")

    # 4. GPT-4 Vision 질문 생성 (선택적)
    if generate_questions:
        print("\n🤖 GPT-4 Vision 질문 생성 중...")
        all_blocks = _generate_questions_for_blocks(
            all_blocks, IMAGE_SAVE_DIR, num_objective, num_subjective
        )

    return all_blocks


def _extract_visual_elements(pdf_path: str, image_save_dir: str) -> List[Dict]:
    """pdfplumber + PyMuPDF를 사용한 시각적 요소 추출"""
    blocks = []
    with pdfplumber.open(pdf_path) as pdf:
        pymupdf_doc = fitz.open(pdf_path)
        for page_num, (plumber_page, pymupdf_page) in enumerate(
            zip(pdf.pages, pymupdf_doc)
        ):
            page_no = page_num + 1
            print(f"  📄 페이지 {page_no} 시각적 요소 추출 중...")
            # 표 추출
            table_blocks = _extract_tables(
                plumber_page, pymupdf_page, page_no, image_save_dir
            )
            blocks.extend(table_blocks)
            # 이미지 추출
            image_blocks = _extract_quality_images(
                pymupdf_page, pymupdf_doc, page_no, image_save_dir
            )
            blocks.extend(image_blocks)
            # 차트 추출 (필요시 주석 해제)
            # from .chart_extractor import _extract_chart_areas
            # existing_bboxes = [b.get("metadata", {}).get("bbox") for b in table_blocks + image_blocks]
            # chart_blocks = _extract_chart_areas(plumber_page, pymupdf_page, page_no, image_save_dir, existing_bboxes)
            # blocks.extend(chart_blocks)
        pymupdf_doc.close()
    return blocks


def _generate_questions_for_blocks(
    blocks: List[Dict], image_save_dir: str, num_objective: int, num_subjective: int
) -> List[Dict]:
    """블록들을 GPT-4 Vision 메시지로 변환하여 질문 생성"""
    try:
        # QuestionGenerator 사용
        question_generator = QuestionGenerator(image_save_dir)
        return question_generator.generate_questions_for_blocks(
            blocks, num_objective, num_subjective
        )
    except Exception as e:
        print(f"❌ 질문 생성 중 오류: {e}")
        return blocks


def _blocks_to_vision_chunks(
    blocks: List[Dict], image_save_dir: str, max_chunk_size: int = 15000
) -> List[Dict]:
    """블록들을 GPT-4 Vision API용 청크로 변환"""
    chunks = []
    current_chunk = {
        "messages": [],
        "metadata": {"pages": set(), "source": "unified_parser"},
        "block_indices": [],
        "current_length": 0,
    }

    def save_current_chunk():
        if current_chunk["messages"]:
            final_metadata = current_chunk["metadata"].copy()
            final_metadata["pages"] = sorted(list(final_metadata["pages"]))
            final_metadata["page"] = (
                final_metadata["pages"][0] if final_metadata["pages"] else 1
            )

            chunks.append(
                {
                    "messages": current_chunk["messages"].copy(),
                    "metadata": final_metadata,
                    "block_indices": current_chunk["block_indices"].copy(),
                }
            )

        current_chunk["messages"].clear()
        current_chunk["metadata"] = {"pages": set(), "source": "unified_parser"}
        current_chunk["block_indices"].clear()
        current_chunk["current_length"] = 0

    for block_idx, block in enumerate(blocks):
        block_type = block.get("type", "unknown")
        content = block.get("content", "")
        metadata = block.get("metadata", {})
        page_no = metadata.get("page", 1)

        # 블록을 메시지로 변환
        message_content = None
        text_length = 0

        if block_type in ["paragraph", "heading", "section"]:
            text_content = str(content) if content else ""
            if text_content.strip():
                if block_type == "heading":
                    text_content = f"# {text_content}"
                elif block_type == "section":
                    text_content = f"## {text_content}"

                message_content = {"type": "text", "text": text_content}
                text_length = len(text_content)

        elif block_type == "table":
            # 표를 텍스트로 변환
            if isinstance(content, dict) and "data" in content:
                table_text = _format_table_as_text(content)
                message_content = {"type": "text", "text": f"[Table]\n{table_text}"}
                text_length = len(table_text)

        elif block_type == "image":
            # 이미지 파일 읽기
            image_path = os.path.join(image_save_dir, block.get("path", ""))
            if os.path.exists(image_path):
                try:
                    with open(image_path, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode("utf-8")
                    message_content = {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded}"},
                    }
                    text_length = 1000  # 이미지는 고정 길이로 계산
                except Exception as e:
                    print(f"이미지 읽기 실패 {image_path}: {e}")
                    continue

        # 청크 크기 확인 및 저장
        if message_content:
            if (
                current_chunk["current_length"] + text_length > max_chunk_size
                and current_chunk["messages"]
            ):
                save_current_chunk()

            current_chunk["messages"].append(message_content)
            current_chunk["metadata"]["pages"].add(page_no)
            current_chunk["block_indices"].append(block_idx)
            current_chunk["current_length"] += text_length

    # 마지막 청크 저장
    save_current_chunk()

    return chunks


def _format_table_as_text(table_data: Dict) -> str:
    """표 데이터를 텍스트로 변환"""
    if not isinstance(table_data, dict) or "data" not in table_data:
        return str(table_data)

    headers = table_data.get("headers", [])
    data = table_data.get("data", [])

    if not data:
        return ""

    table_str = ""
    if headers:
        table_str += " | ".join(str(h) for h in headers) + "\n"
        table_str += "|" + "|".join([":---:"] * len(headers)) + "|\n"

    for row in data:
        table_str += " | ".join(str(cell) for cell in row) + "\n"

    return table_str.strip()


# 테스트용 실행 코드
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        collection_name = sys.argv[2] if len(sys.argv) > 2 else "test_unified"

        if os.path.exists(pdf_path):
            # 질문 생성 옵션 확인
            generate_questions = len(sys.argv) > 3 and sys.argv[3].lower() == "true"

            blocks = parse_pdf_unified(
                pdf_path, collection_name, generate_questions=generate_questions
            )

            print(f"\n📊 통합 파서 결과:")
            print(f"  총 블록: {len(blocks)}개")
            print(
                f"  텍스트 블록: {len([b for b in blocks if b.get('type') in ['paragraph', 'section', 'heading']])}개"
            )
            print(f"  표: {len([b for b in blocks if b.get('type') == 'table'])}개")
            print(f"  이미지: {len([b for b in blocks if b.get('type') == 'image'])}개")

            if generate_questions:
                total_questions = sum(len(b.get("questions", [])) for b in blocks)
                print(f"  생성된 질문: {total_questions}개")
        else:
            print(f"파일을 찾을 수 없습니다: {pdf_path}")
    else:
        print(
            "사용법: python unified_parser.py <pdf_path> [collection_name] [generate_questions:true/false]"
        )
        print("예시: python unified_parser.py 'document.pdf' 'test_collection' true")
