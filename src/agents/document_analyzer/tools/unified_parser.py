"""
통합 PDF 파서 + GPT-4 Vision 질문 생성
- Docling: 텍스트 구조화 (paragraph, section, heading)
- pdfplumber + PyMuPDF: 표 추출 (감지 + 렌더링)
- PyMuPDF: 이미지 추출 (품질 필터링)
- GPT-4 Vision: 자동 질문 생성
"""

import os
from typing import Dict, List

import fitz  # PyMuPDF
import pdfplumber

from utils.naming import filename_to_collection

from .image_extractor import _extract_quality_images
from .table_extractor import _extract_tables
from .text_extractor import _extract_structured_text_with_docling


def parse_pdf_unified(
    pdf_path: str,
    collection_name: str = None,
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
    if collection_name is None:
        normalized_name = filename_to_collection(collection_name)
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
