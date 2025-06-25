"""
TextAnalyzer - 문서 텍스트 추출 및 분석 도구

기존 text_extractor.py의 로직을 BaseTool 구조로 리팩토링
"""

import os
from typing import Any, Dict, List, Optional

import pdfplumber
from docling.document_converter import DocumentConverter

from src.agents.base.tools import BaseTool


class TextAnalyzer(BaseTool):
    """
    텍스트 추출 및 분석 도구

    주요 기능:
    - Docling을 이용한 구조화된 텍스트 추출
    - pdfplumber를 이용한 fallback 텍스트 추출
    - 텍스트 타입 분류 (heading, section, paragraph)
    - 텍스트 정제 및 전처리
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)

        # 기본 설정
        self.config.setdefault("min_text_length", 10)
        self.config.setdefault("use_docling", True)
        self.config.setdefault("fallback_to_pdfplumber", True)
        self.config.setdefault("clean_text", True)
        self.config.setdefault("classify_text_types", True)

    async def execute(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        텍스트 추출의 메인 실행 메서드

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            List[Dict]: 추출된 텍스트 블록들
        """
        if not self._initialized:
            await self.initialize()

        # 1. 파일 검증
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

        # 2. Docling 우선 시도
        if self.config["use_docling"]:
            try:
                blocks = await self._extract_with_docling(pdf_path)
                if blocks:
                    print(f"  📝 Docling 텍스트 블록: {len(blocks)}개")
                    return blocks
            except Exception as e:
                print(f"⚠️ Docling 추출 실패: {e}")

        # 3. pdfplumber fallback
        if self.config["fallback_to_pdfplumber"]:
            try:
                blocks = await self._extract_with_pdfplumber(pdf_path)
                print(f"  📝 pdfplumber 텍스트 블록: {len(blocks)}개")
                return blocks
            except Exception as e:
                print(f"❌ pdfplumber 추출도 실패: {e}")
                raise

        return []

    async def extract_simple_text(self, pdf_path: str) -> str:
        """
        단순 텍스트 추출 (구조 정보 없이)

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            str: 추출된 전체 텍스트
        """
        blocks = await self.execute(pdf_path)  # 메인 execute 메서드 사용

        # 모든 텍스트 블록을 하나로 합치기
        text_parts = []
        for block in blocks:
            if block.get("type") in ["paragraph", "heading", "section"]:
                content = block.get("content") or block.get("title", "")
                if content:
                    text_parts.append(content)

        combined_text = "\n\n".join(text_parts)

        # 텍스트 정제
        if self.config["clean_text"]:
            combined_text = await self.clean_text(combined_text)

        return combined_text

    async def classify_text_type(self, content: str) -> str:
        """
        텍스트 타입 분류 (text_extractor.py의 _classify_text_type과 통합된 로직)

        Args:
            content: 분류할 텍스트

        Returns:
            str: 텍스트 타입 ("heading", "section", "paragraph")
        """
        # text_extractor.py의 _classify_text_type 함수와 동일한 로직 사용
        from .text_extractor import _classify_text_type
        return _classify_text_type(content)

    async def clean_text(self, text: str) -> str:
        """
        텍스트 정제

        Args:
            text: 정제할 텍스트

        Returns:
            str: 정제된 텍스트
        """
        if not text:
            return ""

        import re

        # 연속된 공백 제거
        text = re.sub(r"\s+", " ", text)
        # 연속된 줄바꿈 제거 (최대 2개까지만)
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 앞뒤 공백 제거
        text = text.strip()

        return text

    # 내부 헬퍼 메서드들
    async def _extract_with_docling(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Docling을 사용한 텍스트 추출"""
        converter = DocumentConverter()
        result = converter.convert(pdf_path)
        document = result.document

        blocks = []

        # 텍스트 객체들 처리
        if hasattr(document, "texts"):
            for text_obj in document.texts:
                content = getattr(text_obj, "text", str(text_obj)).strip()
                if content and len(content) > self.config["min_text_length"]:
                    page_no = getattr(text_obj, "page_no", 0) + 1  # 1-indexed

                    # 텍스트 타입 분류
                    text_type = "paragraph"
                    if self.config["classify_text_types"]:
                        text_type = await self.classify_text_type(content)

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

        # 제목 객체들 처리
        if hasattr(document, "titles"):
            for title_obj in document.titles:  # type: ignore
                title = getattr(title_obj, "text", str(title_obj)).strip()
                if title:
                    page_no = getattr(title_obj, "page_no", 0) + 1

                    blocks.append(
                        {
                            "type": "section",
                            "title": title,
                            "content": title,  # content 필드도 추가 (일관성을 위해)
                            "metadata": {
                                "page": page_no,
                                "extraction_method": "docling_section",
                                "source_file": os.path.basename(pdf_path),
                                "text_length": len(title),
                            },
                        }
                    )

        return blocks

    async def _extract_with_pdfplumber(self, pdf_path: str) -> List[Dict[str, Any]]:
        """pdfplumber를 사용한 fallback 텍스트 추출"""
        blocks = []

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_no = page_num + 1
                text_content = page.extract_text()

                if text_content and text_content.strip():
                    # 문단별로 분할
                    paragraphs = [
                        p.strip()
                        for p in text_content.split("\n\n")
                        if p.strip() and len(p) > 20
                    ]

                    for para in paragraphs:
                        # 텍스트 타입 분류
                        text_type = "paragraph"
                        if self.config["classify_text_types"]:
                            text_type = await self.classify_text_type(para)

                        blocks.append(
                            {
                                "type": text_type,
                                "content": para,
                                "metadata": {
                                    "page": page_no,
                                    "extraction_method": "pdfplumber_fallback",
                                    "source_file": os.path.basename(pdf_path),
                                    "text_length": len(para),
                                },
                            }
                        )

        return blocks

    def get_extraction_stats(self, blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """추출 통계 정보 생성"""
        if not blocks:
            return {}

        # 타입별 통계
        type_counts = {}
        total_text_length = 0
        pages = set()

        for block in blocks:
            block_type = block.get("type", "unknown")
            type_counts[block_type] = type_counts.get(block_type, 0) + 1

            content = block.get("content", "")
            total_text_length += len(content)

            page = block.get("metadata", {}).get("page")
            if page:
                pages.add(page)

        return {
            "total_blocks": len(blocks),
            "type_distribution": type_counts,
            "total_text_length": total_text_length,
            "average_block_length": total_text_length / len(blocks) if blocks else 0,
            "page_count": len(pages),
            "extraction_methods": list(
                set(
                    block.get("metadata", {}).get("extraction_method", "unknown")
                    for block in blocks
                )
            ),
        }
