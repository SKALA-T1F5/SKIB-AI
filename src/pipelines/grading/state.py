from typing import List, Dict, Any
from src.pipelines.base.state import BasePipelineState

class GradingState(BasePipelineState, total=False):
    """채점 Pipeline 상태"""
    # 채점 대상
    user_answers: List[Dict[str, Any]]
    test_id: int
    
    # 채점 결과
    scores: List[float]
    feedback: List[str]
