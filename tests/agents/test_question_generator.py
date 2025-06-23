"""
Question Generator Agent 테스트
pytest를 사용하여 QuestionGeneratorAgent의 기능을 테스트합니다.
"""

import os
import json
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
from src.agents.question_generator.agent import QuestionGeneratorAgent, generate_questions_from_document


class TestQuestionGeneratorAgent:
    """QuestionGeneratorAgent 테스트 클래스"""

    @pytest.fixture
    def agent(self):
        """테스트용 QuestionGeneratorAgent 인스턴스"""
        return QuestionGeneratorAgent(collection_name="test_collection")

    @pytest.fixture
    def sample_blocks(self):
        """테스트용 샘플 블록 데이터"""
        return [
            {
                "type": "paragraph",
                "content": "인공지능(AI)은 컴퓨터가 인간의 지능을 모방하는 기술입니다.",
                "page": 1,
                "block_id": 1,
                "questions": [
                    {
                        "type": "OBJECTIVE",
                        "question": "인공지능의 정의는 무엇입니까?",
                        "options": ["A) 컴퓨터 기술", "B) 인간 지능 모방", "C) 로봇 기술", "D) 데이터 분석"],
                        "correct_answer": "B",
                        "difficulty_level": "EASY"
                    }
                ]
            },
            {
                "type": "heading",
                "content": "머신러닝 기초",
                "page": 1,
                "block_id": 2,
                "questions": [
                    {
                        "type": "SUBJECTIVE",
                        "question": "머신러닝과 딥러닝의 차이점을 설명하시오.",
                        "expected_answer": "머신러닝은 데이터로 학습하는 알고리즘이고, 딥러닝은 신경망을 사용하는 머신러닝의 한 분야입니다.",
                        "difficulty_level": "NORMAL"
                    }
                ]
            },
            {
                "type": "table",
                "content": {
                    "headers": ["기술", "특징"],
                    "data": [["AI", "지능 모방"], ["ML", "데이터 학습"]]
                },
                "page": 2,
                "block_id": 3,
                "questions": []
            }
        ]

    @pytest.fixture
    def sample_questions(self):
        """테스트용 샘플 질문 데이터"""
        return [
            {
                "type": "OBJECTIVE",
                "question": "인공지능의 정의는 무엇입니까?",
                "options": ["A) 컴퓨터 기술", "B) 인간 지능 모방", "C) 로봇 기술", "D) 데이터 분석"],
                "correct_answer": "B",
                "difficulty_level": "EASY"
            },
            {
                "type": "SUBJECTIVE",
                "question": "머신러닝과 딥러닝의 차이점을 설명하시오.",
                "expected_answer": "머신러닝은 데이터로 학습하는 알고리즘이고, 딥러닝은 신경망을 사용하는 머신러닝의 한 분야입니다.",
                "difficulty_level": "NORMAL"
            }
        ]

    def test_agent_initialization(self):
        """Agent 초기화 테스트"""
        agent = QuestionGeneratorAgent()
        assert agent.collection_name is None
        assert agent.image_save_dir == "data/images/unified"

        agent_with_collection = QuestionGeneratorAgent("test_collection")
        assert agent_with_collection.collection_name == "test_collection"

    @patch('src.agents.question_generator.agent.QuestionGenerator')
    def test_generate_questions_from_blocks_success(self, mock_question_generator_class, agent, sample_blocks):
        """블록으로부터 문제 생성 성공 테스트"""
        # Mock QuestionGenerator
        mock_generator = Mock()
        mock_question_generator_class.return_value = mock_generator
        mock_generator.generate_questions_for_blocks.return_value = sample_blocks
        
        # Mock 파일 저장 메서드들
        with patch.object(agent, '_save_question_results') as mock_save:
            mock_save.return_value = {
                "status": "completed",
                "questions": [sample_blocks[0]["questions"][0], sample_blocks[1]["questions"][0]],
                "total_questions": 2,
                "files_created": ["test_file.json"]
            }
            
            result = agent.generate_questions_from_blocks(
                blocks=sample_blocks[:2],  # questions가 있는 블록만
                num_objective=1,
                num_subjective=1,
                source_file="test.pdf",
                keywords=["AI", "ML"],
                main_topics=["인공지능", "머신러닝"],
                summary="AI와 ML에 대한 기초 내용"
            )
            
            assert result["status"] == "completed"
            assert result["total_questions"] == 2
            assert len(result["questions"]) == 2

    @patch('src.agents.question_generator.agent.QuestionGenerator')
    def test_generate_questions_from_blocks_failure(self, mock_question_generator_class, agent):
        """블록으로부터 문제 생성 실패 테스트"""
        mock_generator = Mock()
        mock_question_generator_class.return_value = mock_generator
        mock_generator.generate_questions_for_blocks.side_effect = Exception("Question generation failed")
        
        result = agent.generate_questions_from_blocks([])
        
        assert result["status"] == "failed"
        assert "Question generation failed" in result["error"]
        assert result["questions"] == []

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('json.dump')
    def test_save_question_results(self, mock_json_dump, mock_makedirs, mock_open_func, agent, sample_questions):
        """문제 생성 결과 저장 테스트"""
        with patch.object(agent, '_save_test_summary', return_value="summary.json"), \
             patch.object(agent, '_save_test_config', return_value="config.json"):
            
            result = agent._save_question_results(
                questions=sample_questions,
                source_file="test.pdf",
                keywords=["AI", "ML"],
                main_topics=["인공지능"],
                summary="테스트 요약"
            )
            
            assert result["status"] == "completed"
            assert result["total_questions"] == 2
            assert result["objective_count"] == 1
            assert result["subjective_count"] == 1
            assert len(result["files_created"]) == 3  # questions + summary + config

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('json.dump')
    def test_save_test_summary_success(self, mock_json_dump, mock_makedirs, mock_open_func, agent, sample_questions):
        """테스트 요약 저장 성공 테스트"""
        result = agent._save_test_summary(
            questions=sample_questions,
            source_file="test.pdf",
            keywords=["AI", "ML"],
            main_topics=["인공지능"],
            summary="테스트 요약",
            timestamp="20240101_120000"
        )
        
        assert result is not None
        assert "test_test_summary_20240101_120000.json" in result
        mock_makedirs.assert_called()
        mock_json_dump.assert_called()

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('json.dump')
    def test_save_test_summary_failure(self, mock_json_dump, mock_makedirs, mock_open_func, agent):
        """테스트 요약 저장 실패 테스트"""
        mock_json_dump.side_effect = Exception("File save error")
        
        result = agent._save_test_summary(
            questions=[],
            source_file="test.pdf",
            keywords=[],
            main_topics=[],
            summary="",
            timestamp="20240101_120000"
        )
        
        assert result is None

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('json.dump')
    def test_save_test_config_success(self, mock_json_dump, mock_makedirs, mock_open_func, agent, sample_questions):
        """테스트 설정 저장 성공 테스트"""
        result = agent._save_test_config(
            questions=sample_questions,
            source_file="test.pdf",
            timestamp="20240101_120000"
        )
        
        assert result is not None
        assert "test_test_config_20240101_120000.json" in result
        mock_makedirs.assert_called()
        mock_json_dump.assert_called()

    @patch('builtins.open', new_callable=mock_open)
    @patch('os.makedirs')
    @patch('json.dump')
    def test_save_test_config_failure(self, mock_json_dump, mock_makedirs, mock_open_func, agent):
        """테스트 설정 저장 실패 테스트"""
        mock_json_dump.side_effect = Exception("Config save error")
        
        result = agent._save_test_config(
            questions=[],
            source_file="test.pdf",
            timestamp="20240101_120000"
        )
        
        assert result is None

    def test_analyze_content_complexity(self, agent):
        """콘텐츠 복잡도 분석 테스트"""
        # 고급 복잡도
        questions_hard = [{"difficulty_level": "HARD"} for _ in range(3)]
        result = agent._analyze_content_complexity(
            keywords=["key"] * 15,
            main_topics=["topic"] * 8,
            questions=questions_hard
        )
        assert result == "고급"
        
        # 중급 복잡도
        questions_normal = [{"difficulty_level": "NORMAL"} for _ in range(2)]
        result = agent._analyze_content_complexity(
            keywords=["key"] * 7,
            main_topics=["topic"] * 4,
            questions=questions_normal
        )
        assert result == "중급"
        
        # 초급 복잡도
        questions_easy = [{"difficulty_level": "EASY"}]
        result = agent._analyze_content_complexity(
            keywords=["key"] * 3,
            main_topics=["topic"] * 2,
            questions=questions_easy
        )
        assert result == "초급"

    def test_extract_question_topics(self, agent):
        """문제에서 주요 주제 추출 테스트"""
        questions = [
            {"question": "프로세스 관리에 대해 설명하시오."},
            {"question": "업무 처리 절차는 무엇입니까?"},
            {"question": "계약 관리 시스템의 특징을 서술하시오."},
            {"question": "등록 절차를 설명해주세요."}
        ]
        
        result = agent._extract_question_topics(questions)
        
        expected_topics = ["프로세스 관리", "업무 처리", "계약 관리"]
        for topic in expected_topics:
            assert topic in result
        
        # 최대 3개까지만 반환
        assert len(result) <= 3

    def test_extract_question_topics_no_match(self, agent):
        """주제 매칭이 없는 경우 테스트"""
        questions = [
            {"question": "일반적인 질문입니다."},
            {"question": "특별한 키워드가 없는 문제입니다."}
        ]
        
        result = agent._extract_question_topics(questions)
        assert result == []


class TestConvenienceFunctions:
    """편의 함수 테스트"""

    @patch('src.agents.question_generator.agent.QuestionGeneratorAgent')
    def test_generate_questions_from_document(self, mock_agent_class):
        """문서 블록들로부터 문제 생성 편의 함수 테스트"""
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent
        mock_agent.generate_questions_from_blocks.return_value = {
            "status": "completed",
            "questions": [],
            "total_questions": 0
        }
        
        blocks = [{"type": "paragraph", "content": "test"}]
        result = generate_questions_from_document(
            blocks=blocks,
            collection_name="test",
            num_objective=3,
            num_subjective=2,
            source_file="test.pdf",
            keywords=["test"],
            main_topics=["testing"],
            summary="test summary"
        )
        
        mock_agent_class.assert_called_once_with("test")
        mock_agent.generate_questions_from_blocks.assert_called_once_with(
            blocks, 3, 2, "test.pdf", ["test"], ["testing"], "test summary"
        )
        assert result["status"] == "completed"


@pytest.mark.asyncio
class TestQuestionGeneratorIntegration:
    """통합 테스트"""

    def test_full_workflow_mock(self):
        """전체 워크플로우 모의 테스트"""
        agent = QuestionGeneratorAgent("test_collection")
        
        sample_blocks = [
            {
                "type": "paragraph",
                "content": "test content",
                "questions": [{"type": "OBJECTIVE", "question": "test?"}]
            }
        ]
        
        with patch.object(agent.question_generator, 'generate_questions_for_blocks', return_value=sample_blocks), \
             patch.object(agent, '_save_question_results') as mock_save:
            
            mock_save.return_value = {
                "status": "completed",
                "questions": [{"type": "OBJECTIVE", "question": "test?"}],
                "total_questions": 1,
                "files_created": ["test.json"]
            }
            
            result = agent.generate_questions_from_blocks(
                blocks=[{"type": "paragraph", "content": "test"}],
                num_objective=1,
                num_subjective=0
            )
            
            assert result["status"] == "completed"
            assert result["total_questions"] == 1

    def test_error_handling(self):
        """에러 처리 테스트"""
        agent = QuestionGeneratorAgent("test_collection")
        
        with patch.object(agent.question_generator, 'generate_questions_for_blocks') as mock_generate:
            mock_generate.side_effect = Exception("Generation error")
            
            result = agent.generate_questions_from_blocks([])
            
            assert result["status"] == "failed"
            assert "Generation error" in result["error"]

    def test_empty_blocks_handling(self):
        """빈 블록 처리 테스트"""
        agent = QuestionGeneratorAgent("test_collection")
        
        with patch.object(agent.question_generator, 'generate_questions_for_blocks', return_value=[]), \
             patch.object(agent, '_save_question_results') as mock_save:
            
            mock_save.return_value = {
                "status": "completed",
                "questions": [],
                "total_questions": 0,
                "files_created": []
            }
            
            result = agent.generate_questions_from_blocks([])
            
            assert result["status"] == "completed"
            assert result["total_questions"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])