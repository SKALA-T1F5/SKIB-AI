"""
Test Designer Agent 테스트
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.agents.test_designer.agent import TestDesignerAgent, design_test_from_analysis
from src.agents.test_designer.tools.requirement_analyzer import RequirementAnalyzer
from src.agents.test_designer.tools.test_config_generator import TestConfigGenerator


class TestTestDesignerAgent:
    """TestDesignerAgent 테스트 클래스"""

    def test_init(self):
        """Agent 초기화 테스트"""
        agent = TestDesignerAgent()

        assert agent.name == "test_designer"
        assert "requirement_analyzer" in agent.tools
        assert "config_generator" in agent.tools
        assert isinstance(agent.tools["requirement_analyzer"], RequirementAnalyzer)
        assert isinstance(agent.tools["config_generator"], TestConfigGenerator)

    @pytest.mark.asyncio
    async def test_plan(self, sample_user_prompt, sample_keywords):
        """계획 수립 테스트"""
        agent = TestDesignerAgent()

        input_data = {
            "user_prompt": sample_user_prompt,
            "keywords": sample_keywords,
            "document_summary": "테스트 요약",
        }

        plan = await agent.plan(input_data, {})

        assert plan["action"] == "design_test"
        assert "steps" in plan
        assert "analyze_requirements" in plan["steps"]
        assert "generate_test_summary" in plan["steps"]
        assert "create_test_config" in plan["steps"]
        assert "validate_design" in plan["steps"]
        assert plan["input_data"] == input_data

    @pytest.mark.asyncio
    async def test_act_success(
        self,
        sample_user_prompt,
        sample_keywords,
        sample_document_summary,
        sample_document_topics,
        mock_openai_response,
    ):
        """실행 성공 테스트"""
        agent = TestDesignerAgent()

        input_data = {
            "user_prompt": sample_user_prompt,
            "keywords": sample_keywords,
            "document_summary": sample_document_summary,
            "document_topics": sample_document_topics,
        }

        plan = {"input_data": input_data}

        # OpenAI API 모킹
        with patch("openai.ChatCompletion.acreate", return_value=mock_openai_response):
            result = await agent.act(plan, {})

        # 검증
        assert result["status"] == "completed"
        assert "requirements" in result
        assert "test_summary" in result
        assert "test_config" in result

        # 요구사항 검증
        requirements = result["requirements"]
        assert requirements["user_prompt"] == sample_user_prompt
        assert requirements["keywords"] == sample_keywords
        assert requirements["document_summary"] == sample_document_summary

        # 테스트 설정 검증
        test_config = result["test_config"]
        assert test_config["num_questions"] > 0
        assert test_config["num_objective"] > 0
        assert test_config["num_subjective"] > 0
        assert test_config["difficulty"] in ["easy", "medium", "hard"]

    @pytest.mark.asyncio
    async def test_reflect_success(self, sample_test_config):
        """검증 성공 테스트"""
        agent = TestDesignerAgent()

        result = {
            "requirements": {"user_prompt": "테스트"},
            "test_summary": "테스트 요약",
            "test_config": sample_test_config,
        }

        is_valid, feedback = await agent.reflect(result, {})

        assert is_valid is True
        assert "성공적으로 완료" in feedback

    @pytest.mark.asyncio
    async def test_reflect_missing_field(self):
        """필수 필드 누락 검증 테스트"""
        agent = TestDesignerAgent()

        result = {
            "requirements": {"user_prompt": "테스트"},
            # test_summary 누락
            "test_config": {"num_questions": 5},
        }

        is_valid, feedback = await agent.reflect(result, {})

        assert is_valid is False
        assert "test_summary" in feedback
        assert "누락" in feedback

    @pytest.mark.asyncio
    async def test_reflect_invalid_config(self):
        """잘못된 설정 검증 테스트"""
        agent = TestDesignerAgent()

        result = {
            "requirements": {"user_prompt": "테스트"},
            "test_summary": "요약",
            "test_config": {"num_questions": 0},  # 잘못된 문제 수
        }

        is_valid, feedback = await agent.reflect(result, {})

        assert is_valid is False
        assert "유효하지 않은 문제 수" in feedback

    @pytest.mark.asyncio
    async def test_analyze_requirements(self, sample_user_prompt, sample_keywords):
        """요구사항 분석 테스트"""
        agent = TestDesignerAgent()

        input_data = {
            "user_prompt": sample_user_prompt,
            "keywords": sample_keywords,
            "document_summary": "테스트 요약",
            "document_topics": ["주제1", "주제2"],
            "difficulty": "hard",
            "test_type": "objective",
            "time_limit": 90,
        }

        result = await agent._analyze_requirements(input_data)

        assert result["user_prompt"] == sample_user_prompt
        assert result["keywords"] == sample_keywords
        assert result["document_summary"] == "테스트 요약"
        assert result["document_topics"] == ["주제1", "주제2"]
        assert result["target_difficulty"] == "hard"
        assert result["test_type"] == "objective"
        assert result["time_limit"] == 90

    @pytest.mark.asyncio
    async def test_generate_test_summary_success(self, mock_openai_response):
        """테스트 요약 생성 성공 테스트"""
        agent = TestDesignerAgent()

        requirements = {
            "user_prompt": "프로세스 관련 문제 생성",
            "keywords": ["프로세스", "업무"],
            "document_summary": "프로세스 문서",
            "document_topics": ["프로세스 관리"],
            "target_difficulty": "medium",
            "test_type": "mixed",
            "time_limit": 60,
        }

        with patch("openai.ChatCompletion.acreate", return_value=mock_openai_response):
            result = await agent._generate_test_summary(requirements, {})

        assert isinstance(result, str)
        assert len(result) > 0
        assert "테스트 목적" in result or "평가 범위" in result

    @pytest.mark.asyncio
    async def test_generate_test_summary_failure(self):
        """테스트 요약 생성 실패 테스트"""
        agent = TestDesignerAgent()

        requirements = {
            "user_prompt": "테스트 요청",
            "keywords": [],
            "document_summary": "",
            "document_topics": [],
            "target_difficulty": "medium",
            "test_type": "mixed",
            "time_limit": 60,
        }

        # OpenAI API 실패 시뮬레이션
        with patch("openai.ChatCompletion.acreate", side_effect=Exception("API 오류")):
            result = await agent._generate_test_summary(requirements, {})

        # 폴백 요약이 생성되어야 함
        assert isinstance(result, str)
        assert "테스트 목적" in result

    @pytest.mark.asyncio
    async def test_create_test_config_objective_extraction(self):
        """객관식 문제 수 추출 테스트"""
        agent = TestDesignerAgent()

        requirements = {
            "user_prompt": "객관식 10개 문제를 만들어주세요",
            "target_difficulty": "medium",
            "time_limit": 60,
            "test_type": "objective",
            "document_topics": ["주제1"],
            "keywords": ["키워드1"],
        }

        result = await agent._create_test_config("테스트 요약", requirements)

        assert result["num_objective"] == 10
        assert result["num_subjective"] >= 2  # 기본값 또는 조정된 값

    @pytest.mark.asyncio
    async def test_create_test_config_subjective_extraction(self):
        """주관식 문제 수 추출 테스트"""
        agent = TestDesignerAgent()

        requirements = {
            "user_prompt": "주관식 5개 문제를 만들어주세요",
            "target_difficulty": "medium",
            "time_limit": 60,
            "test_type": "subjective",
            "document_topics": ["주제1"],
            "keywords": ["키워드1"],
        }

        result = await agent._create_test_config("테스트 요약", requirements)

        assert result["num_subjective"] == 5
        assert result["num_objective"] >= 3  # 기본값 또는 조정된 값

    @pytest.mark.asyncio
    async def test_create_test_config_difficulty_adjustment(self):
        """난이도별 문제 수 조정 테스트"""
        agent = TestDesignerAgent()

        base_requirements = {
            "user_prompt": "문제를 만들어주세요",
            "time_limit": 60,
            "test_type": "mixed",
            "document_topics": ["주제1"],
            "keywords": ["키워드1"],
        }

        # 쉬운 난이도
        easy_req = {**base_requirements, "target_difficulty": "easy"}
        easy_config = await agent._create_test_config("요약", easy_req)

        # 어려운 난이도
        hard_req = {**base_requirements, "target_difficulty": "hard"}
        hard_config = await agent._create_test_config("요약", hard_req)

        # 어려운 난이도가 더 많은 문제를 가져야 함
        assert hard_config["num_questions"] >= easy_config["num_questions"]


class TestRequirementAnalyzer:
    """RequirementAnalyzer 테스트 클래스"""

    def test_extract_difficulty_easy(self):
        """쉬운 난이도 추출 테스트"""
        analyzer = RequirementAnalyzer()

        prompt = "쉬운 문제를 만들어주세요"
        result = analyzer._extract_difficulty(prompt)

        assert result == "easy"

    def test_extract_difficulty_hard(self):
        """어려운 난이도 추출 테스트"""
        analyzer = RequirementAnalyzer()

        prompt = "고급 수준의 어려운 문제를 만들어주세요"
        result = analyzer._extract_difficulty(prompt)

        assert result == "hard"

    def test_extract_difficulty_default(self):
        """기본 난이도 테스트"""
        analyzer = RequirementAnalyzer()

        prompt = "문제를 만들어주세요"
        result = analyzer._extract_difficulty(prompt)

        assert result == "medium"

    def test_extract_test_type_objective(self):
        """객관식 유형 추출 테스트"""
        analyzer = RequirementAnalyzer()

        prompt = "객관식 문제를 만들어주세요"
        result = analyzer._extract_test_type(prompt)

        assert result == "objective"

    def test_extract_test_type_subjective(self):
        """주관식 유형 추출 테스트"""
        analyzer = RequirementAnalyzer()

        prompt = "주관식 서술형 문제를 만들어주세요"
        result = analyzer._extract_test_type(prompt)

        assert result == "subjective"

    def test_extract_test_type_mixed(self):
        """혼합 유형 추출 테스트"""
        analyzer = RequirementAnalyzer()

        prompt = "객관식과 주관식 문제를 만들어주세요"
        result = analyzer._extract_test_type(prompt)

        assert result == "mixed"

    def test_extract_question_count_objective(self):
        """객관식 문제 수 추출 테스트"""
        analyzer = RequirementAnalyzer()

        prompt = "객관식 8개 만들어주세요"
        result = analyzer._extract_question_count(prompt)

        assert result["objective"] == 8

    def test_extract_question_count_total(self):
        """전체 문제 수 추출 테스트"""
        analyzer = RequirementAnalyzer()

        prompt = "총 10문제 만들어주세요"
        result = analyzer._extract_question_count(prompt)

        total = result["objective"] + result["subjective"]
        assert total == 10

    def test_extract_time_limit_minutes(self):
        """분 단위 시간 추출 테스트"""
        analyzer = RequirementAnalyzer()

        prompt = "30분 시험을 만들어주세요"
        result = analyzer._extract_time_limit(prompt)

        assert result == 30

    def test_extract_time_limit_hours(self):
        """시간 단위 시간 추출 테스트"""
        analyzer = RequirementAnalyzer()

        prompt = "2시간 시험을 만들어주세요"
        result = analyzer._extract_time_limit(prompt)

        assert result == 120  # 2시간 = 120분

    def test_extract_focus_topics(self):
        """집중 주제 추출 테스트"""
        analyzer = RequirementAnalyzer()

        prompt = "프로세스에 대한 문제를 중심으로 만들어주세요"
        keywords = ["프로세스", "업무", "관리"]

        result = analyzer._extract_focus_topics(prompt, keywords)

        assert "프로세스" in result

    def test_extract_special_requirements(self):
        """특수 요구사항 추출 테스트"""
        analyzer = RequirementAnalyzer()

        prompt = "실무 중심의 응용 문제를 만들어주세요"
        result = analyzer._extract_special_requirements(prompt)

        assert "실무중심" in result
        assert "응용문제" in result


class TestTestConfigGenerator:
    """TestConfigGenerator 테스트 클래스"""

    def test_generate_config(self):
        """테스트 설정 생성 테스트"""
        generator = TestConfigGenerator()

        requirements = {
            "difficulty": "medium",
            "test_type": "mixed",
            "question_count": {"objective": 5, "subjective": 3},
            "time_limit": 60,
            "focus_topics": ["프로세스"],
            "special_requirements": ["실무중심"],
        }

        result = generator.generate_config(requirements, "테스트 요약")

        # 기본 구조 검증
        assert "test_info" in result
        assert "question_config" in result
        assert "scoring_config" in result
        assert "generation_config" in result
        assert "constraints" in result
        assert "metadata" in result

        # 문제 설정 검증
        assert result["question_config"]["total_questions"] == 8
        assert result["question_config"]["objective_questions"] == 5
        assert result["question_config"]["subjective_questions"] == 3

        # 채점 설정 검증
        scoring = result["scoring_config"]
        assert scoring["total_points"] == (5 * 2) + (3 * 5)  # 객관식 + 주관식
        assert scoring["passing_score"] == scoring["total_points"] * 0.6

    def test_calculate_distribution(self):
        """문제 분포 계산 테스트"""
        generator = TestConfigGenerator()

        question_count = {"objective": 6, "subjective": 4}
        result = generator._calculate_distribution(question_count)

        assert result["objective"] == 0.6
        assert result["subjective"] == 0.4

    def test_calculate_distribution_zero(self):
        """문제 수가 0인 경우 분포 계산 테스트"""
        generator = TestConfigGenerator()

        question_count = {"objective": 0, "subjective": 0}
        result = generator._calculate_distribution(question_count)

        assert result["objective"] == 0.0
        assert result["subjective"] == 0.0

    def test_determine_question_styles(self):
        """문제 스타일 결정 테스트"""
        generator = TestConfigGenerator()

        special_reqs = ["실무중심", "응용문제"]
        result = generator._determine_question_styles(special_reqs)

        assert "case_study" in result or "practical_application" in result
        assert "application" in result or "problem_solving" in result

    def test_determine_content_emphasis_theory(self):
        """이론 중심 콘텐츠 강조 테스트"""
        generator = TestConfigGenerator()

        special_reqs = ["이론중심"]
        result = generator._determine_content_emphasis(special_reqs)

        # 이론 중심이면 concepts와 facts가 높아야 함
        assert result["concepts"] > 0.3
        assert result["facts"] > 0.3
        assert result["applications"] < 0.2

    def test_determine_content_emphasis_practical(self):
        """실무 중심 콘텐츠 강조 테스트"""
        generator = TestConfigGenerator()

        special_reqs = ["실무중심"]
        result = generator._determine_content_emphasis(special_reqs)

        # 실무 중심이면 applications과 procedures가 높아야 함
        assert result["applications"] > 0.2
        assert result["procedures"] > 0.2
        assert result["facts"] < 0.3


@pytest.mark.asyncio
async def test_design_test_from_analysis_convenience_function(
    sample_keywords,
    sample_document_summary,
    sample_document_topics,
    sample_user_prompt,
    mock_openai_response,
):
    """편의 함수 테스트"""
    with patch(
        "openai.ChatCompletion.acreate", return_value=mock_openai_response
    ), patch("src.agents.test_designer.agent.TestDesignerAgent") as mock_agent_class:

        # Mock 설정
        mock_agent = AsyncMock()
        mock_result = {
            "output": {
                "requirements": {},
                "test_summary": "요약",
                "test_config": {"num_questions": 5},
            }
        }
        mock_agent.execute.return_value = mock_result
        mock_agent_class.return_value = mock_agent

        # 함수 호출
        result = design_test_from_analysis(
            sample_keywords,
            sample_document_summary,
            sample_document_topics,
            sample_user_prompt,
        )

        # 검증
        mock_agent_class.assert_called_once()
        mock_agent.initialize.assert_called_once()
        mock_agent.execute.assert_called_once()
        assert result == mock_result
