"""
Document Analyzer Agent 테스트
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.agents.document_analyzer.agent import DocumentAnalyzerAgent, analyze_document_complete
from src.agents.document_analyzer.state import (
    DocumentAnalyzerState, 
    create_document_analyzer_state,
    get_document_statistics,
    is_analysis_successful,
    get_text_content,
    get_all_questions,
    get_questions_by_type
)


class TestDocumentAnalyzerAgent:
    """DocumentAnalyzerAgent 테스트 클래스"""
    
    def test_init(self, sample_collection_name):
        """Agent 초기화 테스트"""
        agent = DocumentAnalyzerAgent(sample_collection_name)
        
        assert agent.collection_name == sample_collection_name
        assert agent.image_save_dir == f"data/images/{sample_collection_name}"
        assert agent.question_generator is not None
        assert agent.text_analyzer is not None
    
    def test_init_without_collection_name(self):
        """컬렉션명 없이 초기화 테스트"""
        agent = DocumentAnalyzerAgent()
        
        assert agent.collection_name is None
        assert agent.image_save_dir == "data/images/unified"
    
    @patch('src.agents.document_analyzer.agent.parse_pdf_unified')
    def test_analyze_document_success(self, mock_parse, sample_pdf_path, sample_blocks):
        """문서 분석 성공 테스트"""
        # Mock 설정
        mock_parse.return_value = sample_blocks
        
        agent = DocumentAnalyzerAgent("test_collection")
        
        # text_analyzer 모킹
        with patch.object(agent, 'text_analyzer') as mock_text_analyzer:
            mock_text_analyzer.analyze_text.return_value = {
                'keywords': ['프로세스', '업무'],
                'summary': '테스트 요약',
                'main_topics': ['프로세스 관리']
            }
            
            result = agent.analyze_document(sample_pdf_path, extract_keywords=True)
        
        # 검증
        assert isinstance(result, dict)  # TypedDict는 dict로 표현됨
        assert result["pdf_path"] == sample_pdf_path
        assert result["total_blocks"] == 3
        assert result["text_blocks"] == 2  # heading + paragraph
        assert result["table_blocks"] == 1
        assert result["image_blocks"] == 0
        assert result["processing_status"] == "completed"
        assert result["keywords"] == ['프로세스', '업무']
        assert result["summary"] == '테스트 요약'
        assert result["main_topics"] == ['프로세스 관리']
        
        # Mock 호출 확인
        mock_parse.assert_called_once_with(sample_pdf_path, "test_collection", generate_questions=False)
    
    @patch('src.agents.document_analyzer.agent.parse_pdf_unified')
    def test_analyze_document_with_questions(self, mock_parse, sample_pdf_path, sample_blocks):
        """질문 생성과 함께 문서 분석 테스트"""
        # Mock 설정
        blocks_with_questions = sample_blocks.copy()
        blocks_with_questions[0]['questions'] = [
            {"type": "OBJECTIVE", "question": "테스트 문제?"}
        ]
        mock_parse.return_value = blocks_with_questions
        
        agent = DocumentAnalyzerAgent("test_collection")
        
        with patch.object(agent, 'question_generator') as mock_question_gen, \
             patch.object(agent, 'text_analyzer') as mock_text_analyzer:
            
            mock_question_gen.generate_questions_for_blocks.return_value = blocks_with_questions
            mock_text_analyzer.analyze_text.return_value = {
                'keywords': [], 'summary': '', 'main_topics': []
            }
            
            result = agent.analyze_document(
                sample_pdf_path, 
                generate_questions=True,
                num_objective=3,
                num_subjective=2
            )
        
        # 검증
        assert result["questions_generated"] == 1
        mock_question_gen.generate_questions_for_blocks.assert_called_once()
    
    @patch('src.agents.document_analyzer.agent.parse_pdf_unified')
    def test_analyze_document_failure(self, mock_parse, sample_pdf_path):
        """문서 분석 실패 테스트"""
        # Mock에서 예외 발생
        mock_parse.side_effect = FileNotFoundError("파일을 찾을 수 없습니다")
        
        agent = DocumentAnalyzerAgent("test_collection")
        result = agent.analyze_document(sample_pdf_path)
        
        # 검증
        assert result["processing_status"] == "failed"
        assert "파일을 찾을 수 없습니다" in result["error_message"]
    
    @patch('src.agents.document_analyzer.agent.parse_pdf_unified')
    def test_parse_structure_only(self, mock_parse, sample_pdf_path, sample_blocks):
        """구조 파싱만 수행 테스트"""
        mock_parse.return_value = sample_blocks
        
        agent = DocumentAnalyzerAgent("test_collection")
        result = agent.parse_structure_only(sample_pdf_path)
        
        assert result == sample_blocks
        mock_parse.assert_called_once_with(sample_pdf_path, "test_collection", generate_questions=False)
    
    def test_extract_all_text(self, sample_blocks):
        """텍스트 추출 테스트"""
        agent = DocumentAnalyzerAgent("test_collection")
        text = agent._extract_all_text(sample_blocks)
        
        expected_text = "I. 수주사업 Process\n수주사업 프로세스는 다음과 같은 단계로 구성됩니다.\n단계 담당자 기간 계획 PM 1주 실행 개발팀 4주 검토 QA팀 1주"
        assert text == expected_text
    
    def test_table_to_text(self):
        """표를 텍스트로 변환 테스트"""
        agent = DocumentAnalyzerAgent("test_collection")
        
        table_data = {
            "headers": ["이름", "나이"],
            "data": [["홍길동", "30"], ["김철수", "25"]]
        }
        
        result = agent._table_to_text(table_data)
        expected = "이름 나이 홍길동 30 김철수 25"
        assert result == expected
    
    def test_table_to_text_no_headers(self):
        """헤더 없는 표 변환 테스트"""
        agent = DocumentAnalyzerAgent("test_collection")
        
        table_data = {
            "data": [["값1", "값2"], ["값3", "값4"]]
        }
        
        result = agent._table_to_text(table_data)
        expected = "값1 값2 값3 값4"
        assert result == expected


class TestDocumentAnalyzerState:
    """DocumentAnalyzerState 테스트 클래스"""
    
    def test_state_creation(self):
        """상태 생성 테스트"""
        state = create_document_analyzer_state()
        
        assert state["pdf_path"] is None
        assert state["collection_name"] is None
        assert state["blocks"] == []
        assert state["total_blocks"] == 0
        assert state["questions_generated"] == 0
        assert state["keywords"] == []
        assert state["summary"] == ""
        assert state["processing_status"] == "pending"
    
    def test_get_statistics(self, sample_blocks):
        """통계 정보 반환 테스트"""
        state = create_document_analyzer_state()
        state["blocks"] = sample_blocks
        state["total_blocks"] = 3
        state["text_blocks"] = 2
        state["table_blocks"] = 1
        state["image_blocks"] = 0
        state["questions_generated"] = 5
        state["keywords"] = ["키워드1", "키워드2"]
        state["main_topics"] = ["주제1"]
        state["summary"] = "요약"
        state["processing_status"] = "completed"
        state["processing_time"] = 10.5
        
        stats = get_document_statistics(state)
        
        assert stats["total_blocks"] == 3
        assert stats["block_breakdown"]["text"] == 2
        assert stats["block_breakdown"]["table"] == 1
        assert stats["block_breakdown"]["image"] == 0
        assert stats["questions_generated"] == 5
        assert stats["keywords_count"] == 2
        assert stats["topics_count"] == 1
        assert stats["has_summary"] is True
        assert stats["status"] == "completed"
        assert stats["processing_time"] == 10.5
    
    def test_is_successful(self):
        """성공 상태 확인 테스트"""
        state = create_document_analyzer_state()
        
        # 초기 상태 - 성공하지 않음
        assert not is_analysis_successful(state)
        
        # 완료 상태로 변경
        state["processing_status"] = "completed"
        assert is_analysis_successful(state)
        
        # 에러가 있으면 성공하지 않음
        state["error_message"] = "에러 발생"
        assert not is_analysis_successful(state)
    
    def test_get_text_content(self, sample_blocks):
        """텍스트 콘텐츠 추출 테스트"""
        state = create_document_analyzer_state()
        state["blocks"] = sample_blocks
        
        text = get_text_content(state)
        expected = "I. 수주사업 Process\n수주사업 프로세스는 다음과 같은 단계로 구성됩니다."
        assert text == expected
    
    def test_get_questions(self, sample_questions):
        """질문 추출 테스트"""
        state = create_document_analyzer_state()
        state["blocks"] = [
            {"questions": sample_questions[:1]},
            {"questions": sample_questions[1:]}
        ]
        
        questions = get_all_questions(state)
        assert len(questions) == 2
        assert questions[0]["type"] == "OBJECTIVE"
        assert questions[1]["type"] == "SUBJECTIVE"
    
    def test_get_questions_by_type(self, sample_questions):
        """타입별 질문 추출 테스트"""
        state = create_document_analyzer_state()
        state["blocks"] = [{"questions": sample_questions}]
        
        objective_questions = get_questions_by_type(state, "OBJECTIVE")
        subjective_questions = get_questions_by_type(state, "SUBJECTIVE")
        
        assert len(objective_questions) == 1
        assert len(subjective_questions) == 1
        assert objective_questions[0]["type"] == "OBJECTIVE"
        assert subjective_questions[0]["type"] == "SUBJECTIVE"


class TestConvenienceFunctions:
    """편의 함수 테스트"""
    
    @patch('src.agents.document_analyzer.agent.DocumentAnalyzerAgent')
    def test_analyze_document_complete(self, mock_agent_class, sample_pdf_path):
        """문서 완전 분석 편의 함수 테스트"""
        # Mock 설정
        mock_agent = Mock()
        mock_state = create_document_analyzer_state()
        mock_state["processing_status"] = "completed"
        mock_agent.analyze_document.return_value = mock_state
        mock_agent_class.return_value = mock_agent
        
        # 함수 호출
        result = analyze_document_complete(
            sample_pdf_path,
            collection_name="test_collection",
            generate_questions=True,
            extract_keywords=True,
            num_objective=3,
            num_subjective=2
        )
        
        # 검증
        mock_agent_class.assert_called_once_with("test_collection")
        mock_agent.analyze_document.assert_called_once_with(
            sample_pdf_path, True, True, 3, 2
        )
        assert result == mock_state