import logging
import os
from typing import Dict, List

import pdfplumber
from docling.document_converter import DocumentConverter

logger = logging.getLogger(__name__)


def _extract_structured_text_with_docling(pdf_path: str) -> List[Dict]:
    """
    Docling을 사용하여 구조화된 텍스트 추출
    """
    logger.info(
        f"🔍 Docling으로 구조화된 텍스트 추출 시작: {os.path.basename(pdf_path)}"
    )

    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    document = result.document
    blocks = []

    try:
        # 텍스트 객체들 처리
        if hasattr(document, "texts"):
            logger.debug(f"  📄 텍스트 객체 수: {len(document.texts)}개")
            text_count = 0
            for text_obj in document.texts:
                content = getattr(text_obj, "text", str(text_obj)).strip()
                if content and len(content) > 10:  # 최소 길이 조건
                    text_count += 1
                    page_no = getattr(text_obj, "page_no", 0) + 1  # 1-indexed
                    text_type = _classify_text_type(content)  # 통합된 분류 함수 사용

                    blocks.append(
                        {
                            "type": text_type,
                            "content": content,
                            "metadata": {
                                "page": page_no,
                                "extraction_method": "docling_structured",
                                "source_file": os.path.basename(pdf_path),
                                "text_length": len(content),
                            },
                        }
                    )
            logger.info(f"  ✅ 유효한 텍스트 블록: {text_count}개 추출")
        else:
            logger.warning("  ⚠️ 문서에 텍스트 객체가 없습니다")

        # 제목 객체들 처리
        if hasattr(document, "titles"):
            logger.debug(f"  📝 제목 객체 수: {len(document.titles)}개")
            title_count = 0
            for title_obj in document.titles:
                title = getattr(title_obj, "text", str(title_obj)).strip()
                if title:
                    title_count += 1
                    page_no = getattr(title_obj, "page_no", 0) + 1

                    blocks.append(
                        {
                            "type": "section",
                            "title": title,
                            "content": title,  # content 필드 추가 (일관성을 위해)
                            "metadata": {
                                "page": page_no,
                                "extraction_method": "docling_section",
                                "source_file": os.path.basename(pdf_path),
                                "text_length": len(title),
                            },
                        }
                    )
            logger.info(f"  ✅ 제목 블록: {title_count}개 추출")
        else:
            logger.warning("  ⚠️ 문서에 제목 객체가 없습니다")

    except Exception as e:
        logger.warning(f"⚠️ Docling 구조화 추출 중 오류: {e}")
        logger.info("  🔄 pdfplumber 폴백 모드로 전환")
        return _fallback_text_extraction(pdf_path)

    logger.info(f"  📝 Docling 텍스트 블록: {len(blocks)}개")
    return blocks


def _fallback_text_extraction(pdf_path: str) -> List[Dict]:
    """
    Docling 실패 시 pdfplumber로 기본 텍스트 추출
    """
    logger.info(f"🔄 pdfplumber 폴백 텍스트 추출 시작: {os.path.basename(pdf_path)}")
    blocks = []

    with pdfplumber.open(pdf_path) as pdf:
        logger.debug(f"  📄 총 페이지 수: {len(pdf.pages)}개")
        for page_num, page in enumerate(pdf.pages):
            page_no = page_num + 1
            logger.debug(f"  📄 페이지 {page_no} 텍스트 추출 중...")
            text_content = page.extract_text()

            if text_content and text_content.strip():
                # 문단별로 분할
                paragraphs = [
                    p.strip()
                    for p in text_content.split("\n\n")
                    if p.strip() and len(p) > 20  # 최소 길이 조건
                ]

                logger.debug(f"    📝 페이지 {page_no}: {len(paragraphs)}개 문단 추출")

                for para in paragraphs:
                    # 텍스트 타입 분류 적용
                    text_type = _classify_text_type(para)

                    blocks.append(
                        {
                            "type": text_type,  # 단순히 "paragraph"가 아닌 분류된 타입 사용
                            "content": para,
                            "metadata": {
                                "page": page_no,
                                "extraction_method": "pdfplumber_fallback",
                                "source_file": os.path.basename(pdf_path),
                                "text_length": len(para),
                            },
                        }
                    )
            else:
                logger.debug(f"    ⚠️ 페이지 {page_no}: 추출 가능한 텍스트 없음")

    logger.info(f"  📝 pdfplumber 폴백 텍스트 블록: {len(blocks)}개 추출 완료")
    return blocks


def _classify_text_type(content: str) -> str:
    """
    주어진 텍스트의 유형을 'heading', 'section', 'paragraph' 중 하나로 분류합니다.

    - content가 비어있거나 공백만 있으면 'paragraph' 반환
    - 길이가 짧고(100자 미만), 대문자이거나 제목 관련 키워드(챕터, 목차 등)가 포함되어 있거나, 콜론(:)으로 끝나거나 한 줄이면 'heading' 반환
    - 길이가 200자 미만이고, 섹션 관련 키워드(그림, 표, 부록 등)가 포함되어 있으면 'section' 반환
    - 그 외에는 'paragraph' 반환
    """
    if not content or not content.strip():
        return "paragraph"

    content = content.strip()
    content_lower = content.lower()

    # 제목/헤딩 패턴
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

    # 섹션 패턴
    if len(content) < 200 and any(
        keyword in content_lower
        for keyword in ["그림", "figure", "표", "table", "부록", "appendix"]
    ):
        return "section"

    return "paragraph"
