from typing import Any, Dict, Optional

from ..base.state import BaseState


class TestDesignerState(BaseState, total=False):
    """테스트 설계 Agent 전용 상태 - 간소화 버전"""

    # 핵심 결과만 저장
    test_requirements: Optional[Dict[str, Any]]  # requirements 저장
    test_summary: Optional[Dict[str, Any]]  # test_summary 저장
    test_config: Optional[Dict[str, Any]]  # test_config 저장
