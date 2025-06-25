import os
from typing import Dict, List

import pdfplumber
from docling.document_converter import DocumentConverter


def _extract_structured_text_with_docling(pdf_path: str) -> List[Dict]:
    """
    Docling을 사용하여 구조화된 텍스트 추출
    text_analyzer.py의 _extract_with_docling과 통합된 로직
    """
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    document = result.document
    blocks = []
    
    try:
        # 텍스트 객체들 처리 (text_analyzer.py와 동일한 로직)
        if hasattr(document, "texts"):
            for text_obj in document.texts:
                content = getattr(text_obj, "text", str(text_obj)).strip()
                if content and len(content) > 10:  # 최소 길이 조건
                    page_no = getattr(text_obj, "page_no", 0) + 1  # 1-indexed
                    text_type = _classify_text_type(content)  # 통합된 분류 함수 사용
                    
                    blocks.append({
                        "type": text_type,
                        "content": content,
                        "metadata": {
                            "page": page_no,
                            "extraction_method": "docling_structured",
                            "source_file": os.path.basename(pdf_path),
                            "text_length": len(content),  # text_analyzer.py와 일관성
                        },
                    })

        # 제목 객체들 처리 (text_analyzer.py와 동일한 로직)
        if hasattr(document, "titles"):
            for title_obj in document.titles:
                title = getattr(title_obj, "text", str(title_obj)).strip()
                if title:
                    page_no = getattr(title_obj, "page_no", 0) + 1
                    
                    blocks.append({
                        "type": "section",
                        "title": title,
                        "content": title,  # content 필드 추가 (일관성을 위해)
                        "metadata": {
                            "page": page_no,
                            "extraction_method": "docling_section",
                            "source_file": os.path.basename(pdf_path),
                            "text_length": len(title),  # text_analyzer.py와 일관성
                        },
                    })
                    
    except Exception as e:
        print(f"⚠️ Docling 구조화 추출 중 오류: {e}")
        return _fallback_text_extraction(pdf_path)
    
    print(f"  📝 Docling 텍스트 블록: {len(blocks)}개")
    return blocks


def _fallback_text_extraction(pdf_path: str) -> List[Dict]:
    """
    Docling 실패 시 pdfplumber로 기본 텍스트 추출
    text_analyzer.py의 _extract_with_pdfplumber와 통합된 로직
    """
    blocks = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_no = page_num + 1
            text_content = page.extract_text()
            
            if text_content and text_content.strip():
                # 문단별로 분할 (text_analyzer.py와 동일한 로직)
                paragraphs = [
                    p.strip()
                    for p in text_content.split("\n\n")
                    if p.strip() and len(p) > 20  # 최소 길이 조건
                ]
                
                for para in paragraphs:
                    # 텍스트 타입 분류 적용
                    text_type = _classify_text_type(para)
                    
                    blocks.append({
                        "type": text_type,  # 단순히 "paragraph"가 아닌 분류된 타입 사용
                        "content": para,
                        "metadata": {
                            "page": page_no,
                            "extraction_method": "pdfplumber_fallback",
                            "source_file": os.path.basename(pdf_path),
                            "text_length": len(para),  # text_analyzer.py와 일관성
                        },
                    })
    
    return blocks


def _classify_text_type(content: str) -> str:
    """텍스트 타입 분류 - text_analyzer.py의 classify_text_type과 통합된 로직"""
    if not content or not content.strip():
        return "paragraph"

    content = content.strip()
    content_lower = content.lower()

    # 제목/헤딩 패턴 (text_analyzer.py와 동일한 로직)
    if len(content) < 100 and (
        content.isupper()
        or any(
            keyword in content_lower
            for keyword in ["챕터", "chapter", "목차", "제", "부"]
        )
        or content.endswith(":")
        or content.count("\n") == 0
    ):
        return "heading"

    # 섹션 패턴 (text_analyzer.py와 동일한 로직)
    if len(content) < 200 and any(
        keyword in content_lower
        for keyword in ["그림", "figure", "표", "table", "부록", "appendix"]
    ):
        return "section"

    return "paragraph"
