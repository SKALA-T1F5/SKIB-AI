from typing import Optional, Dict, Any, List
from src.agents.base.state import BaseState

class DocumentAnalyzerState(BaseState, total=False):
    """문서 분석 Agent 전용 상태"""
    
    # 문서 정보
    document_id: str
    document_path: str
    document_type: str
    document_metadata: Dict[str, Any]
    
    # 분석 결과
    extracted_text: Optional[str]
    document_structure: Optional[Dict[str, Any]]
    difficulty_assessment: Optional[Dict[str, Any]]
    keywords: Optional[List[str]]
    summary: Optional[str]
    
    # 분석 설정
    analysis_options: Dict[str, Any]