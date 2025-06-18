"""
pytest 설정 및 공통 fixture
"""

import asyncio
import os

# 프로젝트 루트를 Python 경로에 추가
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def event_loop():
    """테스트 세션 전체에서 사용할 이벤트 루프"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_pdf_path():
    """테스트용 PDF 파일 경로"""
    return "data/raw_docs/Process 흐름도_sample_250527.pdf"


@pytest.fixture
def sample_collection_name():
    """테스트용 컬렉션명"""
    return "test_process_sample"


@pytest.fixture
def sample_user_prompt():
    """테스트용 사용자 프롬프트"""
    return "프로세스 관련 객관식 3문제, 주관식 2문제 만들어주세요"


@pytest.fixture
def sample_keywords():
    """테스트용 키워드 목록"""
    return ["프로세스", "업무", "승인", "검토", "완료"]


@pytest.fixture
def sample_document_summary():
    """테스트용 문서 요약"""
    return "이 문서는 수주사업 프로세스에 대한 내용을 다루며, 업무 승인 절차와 검토 과정을 설명합니다."


@pytest.fixture
def sample_document_topics():
    """테스트용 문서 주제"""
    return ["수주사업", "프로세스 관리", "업무 승인", "검토 절차"]


@pytest.fixture
def sample_blocks():
    """테스트용 문서 블록 데이터"""
    return [
        {"type": "heading", "content": "I. 수주사업 Process", "metadata": {"page": 1}},
        {
            "type": "paragraph",
            "content": "수주사업 프로세스는 다음과 같은 단계로 구성됩니다.",
            "metadata": {"page": 1},
        },
        {
            "type": "table",
            "content": {
                "headers": ["단계", "담당자", "기간"],
                "data": [
                    ["계획", "PM", "1주"],
                    ["실행", "개발팀", "4주"],
                    ["검토", "QA팀", "1주"],
                ],
            },
            "metadata": {"page": 2},
        },
    ]


@pytest.fixture
def sample_vision_messages():
    """테스트용 Vision API 메시지"""
    return [
        {"type": "text", "text": "# I. 수주사업 Process"},
        {"type": "text", "text": "수주사업 프로세스는 다음과 같은 단계로 구성됩니다."},
        {
            "type": "text",
            "text": "[Table]\n단계 | 담당자 | 기간\n계획 | PM | 1주\n실행 | 개발팀 | 4주\n검토 | QA팀 | 1주",
        },
    ]


@pytest.fixture
def sample_test_config():
    """테스트용 테스트 설정"""
    return {
        "test_info": {
            "title": "프로세스 중급 평가",
            "description": "수주사업 프로세스에 대한 이해도를 평가합니다.",
            "difficulty": "medium",
            "type": "mixed",
            "estimated_duration": 30,
        },
        "question_config": {
            "total_questions": 5,
            "objective_questions": 3,
            "subjective_questions": 2,
            "distribution": {"objective": 0.6, "subjective": 0.4},
        },
        "scoring": {"objective_points": 2, "subjective_points": 5, "total_points": 16},
    }


@pytest.fixture
def sample_questions():
    """테스트용 생성 문제"""
    return [
        {
            "type": "OBJECTIVE",
            "difficulty_level": "medium",
            "question": "수주사업 프로세스의 첫 번째 단계는?",
            "options": ["계획", "실행", "검토", "완료"],
            "answer": "계획",
            "explanation": "표에 따르면 첫 번째 단계는 계획입니다.",
        },
        {
            "type": "SUBJECTIVE",
            "difficulty_level": "medium",
            "question": "수주사업 프로세스에서 QA팀의 역할을 설명하세요.",
            "answer": "QA팀은 검토 단계에서 1주간 품질 검증을 담당합니다.",
            "grading_criteria": "QA팀의 역할과 기간을 정확히 설명했는지 평가",
        },
    ]


@pytest.fixture
def mock_openai_response():
    """OpenAI API 응답 모킹"""
    return Mock(
        choices=[
            Mock(
                message=Mock(
                    content="테스트 목적: 수주사업 프로세스 이해도 평가\n평가 범위: 프로세스 단계와 담당자 역할\n출제 방향: 실무 중심의 중급 난이도"
                )
            )
        ]
    )


@pytest.fixture
def mock_embedding_model():
    """임베딩 모델 모킹"""
    mock_model = Mock()
    mock_model.encode.return_value = [0.1, 0.2, 0.3, 0.4, 0.5] * 100  # 500차원 벡터
    return mock_model


@pytest.fixture
def mock_weaviate_client():
    """Weaviate 클라이언트 모킹"""
    mock_client = Mock()
    mock_client.collections.list_all.return_value = ["test_collection"]
    mock_client.collections.get.return_value = Mock()
    return mock_client


@pytest.fixture
def temp_output_dir():
    """임시 출력 디렉토리"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def mock_pdf_file():
    """테스트용 PDF 파일 모킹"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"Mock PDF content")
        yield f.name
    os.unlink(f.name)


# 비동기 테스트 헬퍼
def async_test(coro):
    """비동기 함수를 동기적으로 실행하는 헬퍼"""

    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coro(*args, **kwargs))

    return wrapper


# 환경 변수 모킹
@pytest.fixture(autouse=True)
def mock_env_vars():
    """필요한 환경 변수 모킹"""
    with patch.dict(
        os.environ,
        {"OPENAI_API_KEY": "test_key", "WEAVIATE_URL": "http://localhost:8080"},
    ):
        yield


# 테스트 데이터 경로
@pytest.fixture
def test_data_dir():
    """테스트 데이터 디렉토리"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_test_result():
    """테스트용 파이프라인 결과"""
    return {
        "pipeline_info": {
            "collection_name": "test_process_sample",
            "pdf_path": "test.pdf",
            "user_prompt": "테스트 문제 생성",
            "difficulty": "medium",
            "processing_time": 45.5,
            "timestamp": "2024-01-01 12:00:00",
        },
        "document_analysis": {
            "blocks": [],
            "statistics": {
                "total_blocks": 3,
                "block_breakdown": {"text": 2, "table": 1, "image": 0},
            },
            "keywords": ["프로세스", "업무"],
            "summary": "테스트 요약",
            "vectordb_uploaded": True,
        },
        "test_design": {
            "test_summary": "테스트 요약",
            "test_config": {
                "num_questions": 5,
                "num_objective": 3,
                "num_subjective": 2,
            },
        },
        "questions": {
            "questions": [],
            "statistics": {
                "total_questions": 5,
                "objective_questions": 3,
                "subjective_questions": 2,
            },
        },
        "status": "completed",
    }
