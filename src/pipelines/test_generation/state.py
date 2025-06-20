from typing import Any, Dict, List

from src.pipelines.base.state import BasePipelineState


class TestGenerationState(BasePipelineState, total=False):
    """테스트 생성 Pipeline 상태"""

    # 테스트 설정
    test_config: Dict[str, Any]
    document_ids: List[int]

    # 생성 결과
    generated_questions: List[Dict[str, Any]]
    test_structure: Dict[str, Any]
