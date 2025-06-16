from typing import List, Dict
from docling.document_converter import DocumentConverter
import os
import pdfplumber

def _extract_structured_text_with_docling(pdf_path: str) -> List[Dict]:
    """Docling을 사용하여 구조화된 텍스트 추출"""
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    document = result.document
    blocks = []
    try:
        if hasattr(document, 'texts'):
            for text_obj in document.texts:
                content = getattr(text_obj, 'text', str(text_obj)).strip()
                if content and len(content) > 10:
                    page_no = getattr(text_obj, 'page_no', 0) + 1
                    text_type = _classify_text_type(content)
                    blocks.append({
                        "type": text_type,
                        "content": content,
                        "metadata": {
                            "page": page_no,
                            "extraction_method": "docling_structured",
                            "source_file": os.path.basename(pdf_path)
                        }
                    })
        if hasattr(document, 'titles'):
            for title_obj in document.titles:
                title = getattr(title_obj, 'text', str(title_obj)).strip()
                if title:
                    page_no = getattr(title_obj, 'page_no', 0) + 1
                    blocks.append({
                        "type": "section",
                        "title": title,
                        "metadata": {
                            "page": page_no,
                            "extraction_method": "docling_section",
                            "source_file": os.path.basename(pdf_path)
                        }
                    })
    except Exception as e:
        print(f"⚠️ Docling 구조화 추출 중 오류: {e}")
        return _fallback_text_extraction(pdf_path)
    print(f"  📝 Docling 텍스트 블록: {len(blocks)}개")
    return blocks

def _fallback_text_extraction(pdf_path: str) -> List[Dict]:
    """Docling 실패 시 pdfplumber로 기본 텍스트 추출"""
    blocks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_no = page_num + 1
            text_content = page.extract_text()
            if text_content and text_content.strip():
                paragraphs = [p.strip() for p in text_content.split('\n\n') if p.strip() and len(p) > 20]
                for para in paragraphs:
                    blocks.append({
                        "type": "paragraph",
                        "content": para,
                        "metadata": {
                            "page": page_no,
                            "extraction_method": "pdfplumber_fallback",
                            "source_file": os.path.basename(pdf_path)
                        }
                    })
    return blocks

def _classify_text_type(content: str) -> str:
    content_lower = content.lower().strip()
    if (len(content) < 100 and 
        (content.isupper() or 
         any(keyword in content_lower for keyword in ['챕터', 'chapter', '목차', '제', '부']) or
         content.endswith(':') or
         content.count('\n') == 0)):
        return "heading"
    if (len(content) < 200 and 
        any(keyword in content_lower for keyword in ['그림', 'figure', '표', 'table', '부록', 'appendix'])):
        return "section"
    return "paragraph"
