"""
Test Designer Agent 테스트
pytest를 사용하여 TestDesignerAgent의 기능을 테스트합니다.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.agents.test_designer.agent import TestDesignerAgent, design_test_from_analysis


class TestTestDesignerAgent:
    """TestDesignerAgent 테스트 클래스"""

    @pytest.fixture
    def agent(self):
        """테스트용 TestDesignerAgent 인스턴스"""
        return TestDesignerAgent()

    @pytest.fixture
    def sample_input_data(self):
        """테스트용 샘플 입력 데이터"""
        return {
            "keywords": ["AI", "머신러닝", "딥러닝", "알고리즘"],
            "document_summary": "인공지능과 머신러닝에 대한 기초 개념을 설명하는 문서입니다.",
            "document_topics": ["인공지능 개념", "머신러닝 기초", "알고리즘 이해"],
            "user_prompt": "객관식 5개, 주관식 3개 문제를 생성해주세요",
            "difficulty": "medium",
            "test_type": "mixed",
            "time_limit": 60
        }

    @pytest.fixture
    def sample_state(self):
        """테스트용 샘플 상태"""
        from src.agents.base.state import TestDesignerState
        return TestDesignerState()

    def test_agent_initialization(self, agent):
        """Agent 초기화 테스트"""
        assert agent.name == "test_designer"
        assert "requirement_analyzer" in agent.tools
        assert "config_generator" in agent.tools

    @pytest.mark.asyncio
    async def test_plan(self, agent, sample_input_data, sample_state):
        """테스트 설계 계획 수립 테스트"""
        result = await agent.plan(sample_input_data, sample_state)
        
        assert result["action"] == "design_test"
        assert "steps" in result
        assert "analyze_requirements" in result["steps"]
        assert "generate_test_summary" in result["steps"]
        assert "create_test_config" in result["steps"]
        assert "validate_design" in result["steps"]
        assert result["input_data"] == sample_input_data

    @pytest.mark.asyncio
    async def test_act_success(self, agent, sample_input_data, sample_state):
        """테스트 설계 실행 성공 테스트"""
        # Mock methods
        with patch.object(agent, '_analyze_requirements') as mock_analyze, \
             patch.object(agent, '_generate_test_summary') as mock_summary, \
             patch.object(agent, '_create_test_config') as mock_config, \
             patch.object(agent, 'update_progress'):
            
            mock_analyze.return_value = {"analyzed": "requirements"}
            mock_summary.return_value = {"test_title": "AI 기초 테스트", "test_summary": "AI 기초 평가"}
            mock_config.return_value = {"num_questions": 8, "difficulty": "medium"}
            
            plan = {"input_data": sample_input_data}
            result = await agent.act(plan, sample_state)
            
            assert result["status"] == "completed"
            assert "requirements" in result
            assert "test_summary" in result
            assert "test_config" in result

    @pytest.mark.asyncio
    async def test_reflect_success(self, agent, sample_state):
        """결과 검증 성공 테스트"""
        result = {
            "requirements": {"test": "data"},
            "test_summary": {"test_title": "Test", "test_summary": "Summary"},
            "test_config": {"num_questions": 5}
        }
        
        is_valid, message = await agent.reflect(result, sample_state)
        
        assert is_valid is True
        assert "성공적으로 완료" in message

    @pytest.mark.asyncio
    async def test_reflect_missing_fields(self, agent, sample_state):
        """결과 검증 실패 테스트 - 필수 필드 누락"""
        result = {
            "requirements": {"test": "data"},
            "test_summary": {"test_title": "Test", "test_summary": "Summary"}
            # test_config 누락
        }
        
        is_valid, message = await agent.reflect(result, sample_state)
        
        assert is_valid is False
        assert "test_config" in message

    @pytest.mark.asyncio
    async def test_reflect_no_questions(self, agent, sample_state):
        """결과 검증 실패 테스트 - 문제 수 없음"""
        result = {
            "requirements": {"test": "data"},
            "test_summary": {"test_title": "Test", "test_summary": "Summary"},
            "test_config": {"num_questions": 0}
        }
        
        is_valid, message = await agent.reflect(result, sample_state)
        
        assert is_valid is False
        assert "문제 수가 설정되지 않았습니다" in message

    @pytest.mark.asyncio
    async def test_analyze_requirements(self, agent, sample_input_data):
        """요구사항 분석 테스트"""
        result = await agent._analyze_requirements(sample_input_data)
        
        assert result["user_prompt"] == sample_input_data["user_prompt"]
        assert result["keywords"] == sample_input_data["keywords"]
        assert result["document_summary"] == sample_input_data["document_summary"]
        assert result["document_topics"] == sample_input_data["document_topics"]
        assert result["target_difficulty"] == "medium"
        assert result["test_type"] == "mixed"
        assert result["time_limit"] == 60

    @pytest.mark.asyncio
    async def test_generate_test_summary_success(self, agent):
        """테스트 요약 생성 성공 테스트"""
        requirements = {
            "user_prompt": "객관식 5개 문제 생성",
            "keywords": ["AI", "ML"],
            "document_summary": "AI 기초",
            "document_topics": ["AI 개념"],
            "target_difficulty": "medium",
            "test_type": "objective",
            "time_limit": 30
        }
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"test_title": "AI 기초 테스트", "test_summary": "AI 기초 개념 평가"}'
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response
            
            result = await agent._generate_test_summary(requirements, {})
            
            assert "test_title" in result
            assert "test_summary" in result

    @pytest.mark.asyncio
    async def test_generate_test_summary_failure(self, agent):
        """테스트 요약 생성 실패 테스트"""
        requirements = {
            "user_prompt": "테스트 생성",
            "keywords": [],
            "document_summary": "",
            "document_topics": [],
            "target_difficulty": "medium",
            "test_type": "mixed",
            "time_limit": 60
        }
        
        with patch('openai.AsyncOpenAI') as mock_openai:
            mock_openai.side_effect = Exception("API Error")
            
            result = await agent._generate_test_summary(requirements, {})
            
            # 실패 시 기본 요약 반환
            assert isinstance(result, str)
            assert "테스트 목적" in result

    @pytest.mark.asyncio
    async def test_create_test_config_basic(self, agent):
        """기본 테스트 설정 생성 테스트"""
        test_summary = {"test_title": "Test", "test_summary": "Summary"}
        requirements = {
            "user_prompt": "기본 테스트 생성",
            "target_difficulty": "medium",
            "time_limit": 60,
            "test_type": "mixed",
            "document_topics": ["topic1", "topic2"],
            "keywords": ["key1", "key2"]
        }
        
        result = await agent._create_test_config(test_summary, requirements)
        
        assert result["difficulty"] == "medium"
        assert result["time_limit"] == 60
        assert result["test_type"] == "mixed"
        assert result["num_questions"] == 8  # 기본값: 5 + 3
        assert result["num_objective"] == 5
        assert result["num_subjective"] == 3

    @pytest.mark.asyncio
    async def test_create_test_config_with_numbers(self, agent):
        """숫자가 포함된 사용자 프롬프트 테스트"""
        test_summary = {"test_title": "Test", "test_summary": "Summary"}
        requirements = {
            "user_prompt": "객관식 10개, 주관식 5개 문제를 생성해주세요",
            "target_difficulty": "hard",
            "time_limit": 90,
            "test_type": "mixed",
            "document_topics": ["topic1"],
            "keywords": ["key1"]
        }
        
        result = await agent._create_test_config(test_summary, requirements)
        
        # hard 난이도로 인해 조정된 값
        assert result["num_objective"] == 13  # 10 + 3
        assert result["num_subjective"] == 7   # 5 + 2
        assert result["num_questions"] == 20

    @pytest.mark.asyncio
    async def test_create_test_config_easy_difficulty(self, agent):
        """쉬운 난이도 테스트 설정"""
        test_summary = {"test_title": "Test", "test_summary": "Summary"}
        requirements = {
            "user_prompt": "쉬운 테스트 생성",
            "target_difficulty": "easy",
            "time_limit": 30,
            "test_type": "mixed",
            "document_topics": ["topic1"],
            "keywords": ["key1"]
        }
        
        result = await agent._create_test_config(test_summary, requirements)
        
        # easy 난이도로 인해 조정된 값
        assert result["num_objective"] == 3  # max(3, 5-2)
        assert result["num_subjective"] == 2  # max(2, 3-1)

    @pytest.mark.asyncio
    async def test_create_test_config_scoring(self, agent):
        """점수 계산 테스트"""
        test_summary = {"test_title": "Test", "test_summary": "Summary"}
        requirements = {
            "user_prompt": "테스트 생성",
            "target_difficulty": "medium",
            "time_limit": 60,
            "test_type": "mixed",
            "document_topics": ["topic1"],
            "keywords": ["key1"]
        }
        
        result = await agent._create_test_config(test_summary, requirements)
        
        scoring = result["scoring"]
        assert scoring["objective_points"] == 2
        assert scoring["subjective_points"] == 5
        
        # 총점 계산: (객관식 수 * 2) + (주관식 수 * 5)
        expected_total = (result["num_objective"] * 2) + (result["num_subjective"] * 5)
        assert scoring["total_points"] == expected_total


class TestConvenienceFunctions:
    """편의 함수 테스트"""

    @patch('src.agents.test_designer.agent.TestDesignerAgent')
    @pytest.mark.asyncio
    async def test_design_test_from_analysis(self, mock_agent_class):
        """문서 분석 결과로부터 테스트 설계 편의 함수 테스트"""
        mock_agent = Mock()
        mock_agent_class.return_value = mock_agent
        
        # AsyncMock으로 비동기 메서드 모킹
        mock_agent.initialize = AsyncMock()
        mock_agent.execute = AsyncMock(return_value={"status": "completed"})
        
        result = design_test_from_analysis(
            keywords=["AI", "ML"],
            document_summary="AI 기초",
            document_topics=["AI 개념"],
            user_prompt="테스트 생성",
            difficulty="medium",
            test_type="mixed",
            time_limit=60
        )
        
        assert result == {"status": "completed"}


@pytest.mark.asyncio
class TestTestDesignerIntegration:
    """통합 테스트"""

    async def test_full_workflow_mock(self):
        """전체 워크플로우 모의 테스트"""
        agent = TestDesignerAgent()
        
        input_data = {
            "keywords": ["test"],
            "document_summary": "test summary",
            "document_topics": ["test topic"],
            "user_prompt": "객관식 3개 문제 생성",
            "difficulty": "medium",
            "test_type": "objective",
            "time_limit": 30
        }
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"test_title": "테스트", "test_summary": "테스트 요약"}'
        
        with patch('openai.AsyncOpenAI') as mock_openai, \
             patch.object(agent, 'update_progress'):
            
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client
            mock_client.chat.completions.create.return_value = mock_response
            
            from src.agents.base.state import TestDesignerState
            state = TestDesignerState()
            
            # 전체 워크플로우 실행
            plan = await agent.plan(input_data, state)
            result = await agent.act(plan, state)
            is_valid, message = await agent.reflect(result, state)
            
            assert result["status"] == "completed"
            assert is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])