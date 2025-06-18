"""
TextAnalyzer 테스트
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.agents.document_analyzer.tools.text_analyzer import TextAnalyzer


class TestTextAnalyzer:
    """TextAnalyzer 테스트 클래스"""

    @pytest.fixture
    def analyzer(self):
        """TextAnalyzer 픽스처"""
        return TextAnalyzer(
            {
                "use_docling": True,
                "fallback_to_pdfplumber": True,
                "classify_text_types": True,
                "min_text_length": 10,
            }
        )

    @pytest.fixture
    def sample_blocks(self):
        """샘플 텍스트 블록 데이터"""
        return [
            {
                "type": "heading",
                "content": "제1장 개요",
                "metadata": {"page": 1, "text_length": 7},
            },
            {
                "type": "paragraph",
                "content": "이것은 테스트용 문단입니다. 여러 문장이 포함되어 있습니다.",
                "metadata": {"page": 1, "text_length": 32},
            },
            {
                "type": "section",
                "content": "그림 1. 시스템 구조도",
                "metadata": {"page": 2, "text_length": 12},
            },
        ]

    @pytest.mark.asyncio
    async def test_initialization(self, analyzer):
        """초기화 테스트"""
        assert not analyzer.is_initialized()
        await analyzer.initialize()
        assert analyzer.is_initialized()
        assert analyzer.config["use_docling"] is True
        assert analyzer.config["min_text_length"] == 10

    @pytest.mark.asyncio
    async def test_classify_text_type_heading(self, analyzer):
        """텍스트 타입 분류 - 제목 테스트"""
        await analyzer.initialize()

        # 제목 패턴들
        heading_texts = ["제1장 개요", "CHAPTER 1: INTRODUCTION", "목차:", "1부 시작"]

        for text in heading_texts:
            result = await analyzer.classify_text_type(text)
            assert result == "heading", f"'{text}'는 heading이어야 함"

    @pytest.mark.asyncio
    async def test_classify_text_type_section(self, analyzer):
        """텍스트 타입 분류 - 섹션 테스트"""
        await analyzer.initialize()

        # 섹션 패턴들
        section_texts = [
            "그림 1. 시스템 구조",
            "표 2-1. 비교 결과",
            "Figure 3.2 Architecture",
            "부록 A. 참고자료",
        ]

        for text in section_texts:
            result = await analyzer.classify_text_type(text)
            assert result == "section", f"'{text}'는 section이어야 함"

    @pytest.mark.asyncio
    async def test_classify_text_type_paragraph(self, analyzer):
        """텍스트 타입 분류 - 문단 테스트"""
        await analyzer.initialize()

        # 문단 패턴들
        paragraph_texts = [
            "이것은 일반적인 문단입니다. 여러 문장으로 구성되어 있으며 내용이 길어집니다.",
            "시스템은 다음과 같은 구조로 되어 있습니다. 첫째로 사용자 인터페이스가 있고, 둘째로 비즈니스 로직이 있습니다.",
        ]

        for text in paragraph_texts:
            result = await analyzer.classify_text_type(text)
            assert result == "paragraph", f"'{text}'는 paragraph여야 함"

    @pytest.mark.asyncio
    async def test_clean_text(self, analyzer):
        """텍스트 정제 테스트"""
        await analyzer.initialize()

        # 정제 전 텍스트 (여러 공백, 줄바꿈 포함)
        dirty_text = (
            "  이것은   테스트    텍스트입니다.  \n\n\n\n  여러 줄바꿈이   있습니다.  "
        )

        cleaned = await analyzer.clean_text(dirty_text)

        # 검증
        assert "   " not in cleaned  # 3개 이상 연속 공백 없음
        assert "\n\n\n" not in cleaned  # 3개 이상 연속 줄바꿈 없음
        assert not cleaned.startswith(" ")  # 앞 공백 제거
        assert not cleaned.endswith(" ")  # 뒤 공백 제거
        assert "이것은 테스트 텍스트입니다." in cleaned

    @pytest.mark.asyncio
    async def test_extract_simple_text(self, analyzer, sample_blocks):
        """단순 텍스트 추출 테스트"""
        # extract_structured_text를 Mock으로 대체
        with patch.object(
            analyzer, "extract_structured_text", new_callable=AsyncMock
        ) as mock_extract:
            mock_extract.return_value = sample_blocks

            await analyzer.initialize()
            result = await analyzer.extract_simple_text("test.pdf")

            # 검증
            assert "제1장 개요" in result
            assert "이것은 테스트용 문단입니다" in result
            assert "그림 1. 시스템 구조도" in result
            mock_extract.assert_called_once_with("test.pdf")

    @pytest.mark.asyncio
    async def test_extract_structured_text_with_docling_success(self, analyzer):
        """Docling을 이용한 구조화된 텍스트 추출 성공 테스트"""
        # Docling Mock 설정
        mock_doc = Mock()
        mock_text_obj = Mock()
        mock_text_obj.text = "테스트 내용입니다."
        mock_text_obj.page_no = 0
        mock_doc.texts = [mock_text_obj]
        mock_doc.titles = []

        mock_result = Mock()
        mock_result.document = mock_doc

        with patch(
            "src.agents.document_analyzer.tools.text_analyzer.DocumentConverter"
        ) as mock_converter:
            mock_instance = mock_converter.return_value
            mock_instance.convert.return_value = mock_result

            with patch("os.path.exists", return_value=True):
                await analyzer.initialize()
                result = await analyzer.extract_structured_text("test.pdf")

                # 검증
                assert len(result) == 1
                assert result[0]["content"] == "테스트 내용입니다."
                assert result[0]["metadata"]["page"] == 1
                assert (
                    result[0]["metadata"]["extraction_method"] == "docling_structured"
                )

    @pytest.mark.asyncio
    async def test_extract_structured_text_docling_fallback(self, analyzer):
        """Docling 실패 시 pdfplumber fallback 테스트"""
        # Docling이 실패하도록 설정
        with patch(
            "src.agents.document_analyzer.tools.text_analyzer.DocumentConverter"
        ) as mock_converter:
            mock_converter.side_effect = Exception("Docling failed")

            # pdfplumber Mock 설정
            mock_page = Mock()
            mock_page.extract_text.return_value = (
                "pdfplumber로 추출된 텍스트입니다.\n\n이것은 두 번째 문단입니다."
            )

            mock_pdf = Mock()
            mock_pdf.pages = [mock_page]
            mock_pdf.__enter__ = Mock(return_value=mock_pdf)
            mock_pdf.__exit__ = Mock(return_value=None)

            with patch("pdfplumber.open", return_value=mock_pdf):
                with patch("os.path.exists", return_value=True):
                    await analyzer.initialize()
                    result = await analyzer.extract_structured_text("test.pdf")

                    # 검증
                    assert len(result) == 1  # 하나의 문단이 추출됨
                    assert "pdfplumber로 추출된 텍스트입니다." in result[0]["content"]
                    assert (
                        result[0]["metadata"]["extraction_method"]
                        == "pdfplumber_fallback"
                    )

    @pytest.mark.asyncio
    async def test_extract_structured_text_file_not_found(self, analyzer):
        """파일이 없을 때 예외 처리 테스트"""
        with patch("os.path.exists", return_value=False):
            await analyzer.initialize()

            with pytest.raises(FileNotFoundError, match="PDF 파일을 찾을 수 없습니다"):
                await analyzer.extract_structured_text("nonexistent.pdf")

    def test_get_extraction_stats(self, analyzer, sample_blocks):
        """추출 통계 정보 테스트"""
        stats = analyzer.get_extraction_stats(sample_blocks)

        # 검증
        assert stats["total_blocks"] == 3
        assert stats["type_distribution"]["heading"] == 1
        assert stats["type_distribution"]["paragraph"] == 1
        assert stats["type_distribution"]["section"] == 1
        assert stats["total_text_length"] == 51  # 7 + 32 + 12
        assert stats["page_count"] == 2
        assert stats["average_block_length"] == 51 / 3

    def test_get_extraction_stats_empty(self, analyzer):
        """빈 블록 리스트에 대한 통계 테스트"""
        stats = analyzer.get_extraction_stats([])
        assert stats == {}
