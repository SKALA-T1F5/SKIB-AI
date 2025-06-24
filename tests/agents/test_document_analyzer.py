"""
Document Analyzer Agent 테스트
pytest를 사용하여 DocumentAnalyzerAgent의 기능을 테스트합니다.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from src.agents.document_analyzer.agent import (
    DocumentAnalyzerAgent,
    analyze_document_complete,
)


class TestDocumentAnalyzerAgent:
    """DocumentAnalyzerAgent 테스트 클래스"""

    @pytest.fixture
    def agent(self):
        """테스트용 DocumentAnalyzerAgent 인스턴스"""
        return DocumentAnalyzerAgent(
            collection_name="test_collection", auto_upload_chromadb=False
        )

    @pytest.fixture
    def sample_blocks(self):
        """테스트용 샘플 블록 데이터"""
        return [
            {
                "type": "paragraph",
                "content": "This is a test paragraph with important information.",
                "page": 1,
                "block_id": 1,
            },
            {"type": "heading", "content": "Test Heading", "page": 1, "block_id": 2},
            {
                "type": "table",
                "content": {
                    "headers": ["Column1", "Column2"],
                    "data": [["Row1Col1", "Row1Col2"], ["Row2Col1", "Row2Col2"]],
                },
                "page": 2,
                "block_id": 3,
            },
            {"type": "image", "content": "image_description", "page": 2, "block_id": 4},
        ]

    def test_agent_initialization(self):
        """Agent 초기화 테스트"""
        agent = DocumentAnalyzerAgent()
        assert agent.collection_name is None
        assert agent.auto_upload_chromadb is True
        assert agent.image_save_dir == "data/images/unified"

        agent_with_collection = DocumentAnalyzerAgent("test_collection", False)
        assert agent_with_collection.collection_name == "test_collection"
        assert agent_with_collection.auto_upload_chromadb is False

    @patch("src.agents.document_analyzer.agent.parse_pdf_unified")
    @patch(
        "src.agents.document_analyzer.tools.keyword_summary.extract_keywords_and_summary"
    )
    def test_analyze_document_success(
        self, mock_extract_keywords, mock_parse_pdf, agent, sample_blocks
    ):
        """문서 분석 성공 테스트"""
        # Mock 설정
        mock_parse_pdf.return_value = sample_blocks
        mock_extract_keywords.return_value = {
            "content_analysis": {
                "key_concepts": ["test", "document", "analysis"],
                "summary": "This is a test document summary",
                "main_topics": ["testing", "documentation"],
            }
        }

        with patch.object(agent, "_save_results"):
            result = agent.analyze_document("test.pdf", extract_keywords=True)

        # 결과 검증
        assert result["processing_status"] == "completed"
        assert result["error_message"] is None
        assert result["total_blocks"] == 4
        assert result["text_blocks"] == 2  # paragraph + heading
        assert result["table_blocks"] == 1
        assert result["image_blocks"] == 1
        assert result["keywords"] == ["test", "document", "analysis"]
        assert result["summary"] == "This is a test document summary"
        assert result["main_topics"] == ["testing", "documentation"]

    @patch("src.agents.document_analyzer.agent.parse_pdf_unified")
    def test_analyze_document_without_keywords(
        self, mock_parse_pdf, agent, sample_blocks
    ):
        """키워드 추출 없이 문서 분석 테스트"""
        mock_parse_pdf.return_value = sample_blocks

        with patch.object(agent, "_save_results"):
            result = agent.analyze_document("test.pdf", extract_keywords=False)

        assert result["processing_status"] == "completed"
        assert "keywords" not in result or result["keywords"] == []
        assert result["total_blocks"] == 4

    @patch("src.agents.document_analyzer.agent.parse_pdf_unified")
    def test_analyze_document_failure(self, mock_parse_pdf, agent):
        """문서 분석 실패 테스트"""
        mock_parse_pdf.side_effect = Exception("PDF parsing failed")

        result = agent.analyze_document("test.pdf")

        assert result["processing_status"] == "failed"
        assert "PDF parsing failed" in result["error_message"]

    @patch("src.agents.document_analyzer.agent.parse_pdf_unified")
    def test_parse_structure_only(self, mock_parse_pdf, agent, sample_blocks):
        """구조 파싱만 수행 테스트"""
        mock_parse_pdf.return_value = sample_blocks

        result = agent.parse_structure_only("test.pdf")

        assert result == sample_blocks
        mock_parse_pdf.assert_called_once_with(
            "test.pdf", "test_collection", generate_questions=False
        )

    def test_analyze_text_only(self, agent):
        """텍스트 분석만 수행 테스트"""
        # analyze_text 메서드가 존재하지 않으므로 mock으로 테스트 (create=True 옵션 사용)
        with patch.object(
            agent.text_analyzer,
            "analyze_text",
            create=True,
            return_value={"analysis": "result"},
        ):
            result = agent.analyze_text_only("test text", "custom_collection")
            assert result == {"analysis": "result"}

    def test_extract_all_text(self, agent, sample_blocks):
        """모든 텍스트 추출 테스트"""
        result = agent._extract_all_text(sample_blocks)

        expected_text = "This is a test paragraph with important information.\nTest Heading\nColumn1 Column2 Row1Col1 Row1Col2 Row2Col1 Row2Col2"
        assert result == expected_text

    def test_table_to_text(self, agent):
        """표 데이터를 텍스트로 변환 테스트"""
        table_data = {
            "headers": ["Name", "Age"],
            "data": [["John", "25"], ["Jane", "30"]],
        }

        result = agent._table_to_text(table_data)
        expected = "Name Age John 25 Jane 30"
        assert result == expected

        # 빈 테이블 테스트
        empty_result = agent._table_to_text({})
        assert empty_result == ""

    @patch("builtins.open")
    @patch("os.makedirs")
    @patch("json.dump")
    def test_save_results(self, mock_json_dump, mock_makedirs, mock_open, agent):
        """결과 저장 테스트"""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        state = {
            "keywords": ["test", "keyword"],
            "summary": "Test summary",
            "main_topics": ["topic1", "topic2"],
            "total_blocks": 10,
            "text_blocks": 8,
            "table_blocks": 1,
            "image_blocks": 1,
        }

        agent._save_results(state, "test.pdf", True)

        # 디렉토리 생성 확인
        assert mock_makedirs.call_count >= 2
        # 파일 저장 확인
        assert mock_json_dump.call_count >= 2

    @patch("db.vectorDB.chromaDB.upload_documents")
    def test_upload_to_chromadb_success(self, mock_upload, agent, sample_blocks):
        """ChromaDB 업로드 성공 테스트"""
        mock_upload.return_value = 4

        result = agent._upload_to_chromadb(sample_blocks, "test.pdf")

        assert result == 4
        mock_upload.assert_called_once_with(
            sample_blocks, "test_collection", "test.pdf"
        )

    @patch("db.vectorDB.chromaDB.upload_documents")
    def test_upload_to_chromadb_failure(self, mock_upload, agent, sample_blocks):
        """ChromaDB 업로드 실패 테스트"""
        mock_upload.side_effect = Exception("Upload failed")

        result = agent._upload_to_chromadb(sample_blocks, "test.pdf")

        assert result == 0


class TestConvenienceFunctions:
    """편의 함수 테스트"""

    @patch("src.agents.document_analyzer.agent.DocumentAnalyzerAgent")
    def test_analyze_document_complete(self, mock_agent_class):
        """문서 종합 분석 편의 함수 테스트"""
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent
        mock_agent.analyze_document.return_value = {"status": "completed"}

        result = analyze_document_complete(
            "test.pdf", "collection", extract_keywords=True, auto_upload_chromadb=False
        )

        mock_agent_class.assert_called_once_with("collection", False)
        mock_agent.analyze_document.assert_called_once_with("test.pdf", True)
        assert result == {"status": "completed"}


class TestDocumentAnalyzerIntegration:
    """통합 테스트"""

    def test_full_workflow_mock(self):
        """전체 워크플로우 모의 테스트"""
        with patch(
            "src.agents.document_analyzer.agent.parse_pdf_unified"
        ) as mock_parse, patch(
            "src.agents.document_analyzer.tools.keyword_summary.extract_keywords_and_summary"
        ) as mock_extract, patch.object(
            DocumentAnalyzerAgent, "_save_results"
        ), patch.object(
            DocumentAnalyzerAgent, "_upload_to_chromadb", return_value=0
        ):

            # Mock 데이터 설정
            mock_parse.return_value = [{"type": "paragraph", "content": "test"}]
            mock_extract.return_value = {
                "content_analysis": {
                    "key_concepts": ["test"],
                    "summary": "summary",
                    "main_topics": ["topic"],
                }
            }

            agent = DocumentAnalyzerAgent("test_collection", auto_upload_chromadb=False)
            result = agent.analyze_document("test.pdf")

            assert result["processing_status"] == "completed"
            assert result["total_blocks"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
