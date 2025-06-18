"""
문서 분석 Agent 상태 관리
"""

from typing import List, Dict, Optional
from ..base.state import BaseState


class DocumentAnalyzerState(BaseState, total=False):
    """문서 분석 상태"""
    
    # 입력 정보
    pdf_path: Optional[str]
    collection_name: Optional[str]
    
    # 분석 결과
    blocks: List[Dict]
    total_blocks: int
    text_blocks: int
    table_blocks: int
    image_blocks: int
    
    # 질문 생성 결과
    questions_generated: int
    
    # 텍스트 분석 결과
    keywords: List[str]
    main_topics: List[str]
    summary: str
    
    # 처리 상태
    processing_status: str  # pending, processing, completed, failed
    error_message: Optional[str]
    
    # 메타데이터
    processing_time: float
    image_save_dir: str
    

def get_document_statistics(state: DocumentAnalyzerState) -> Dict:
    """분석 통계 반환"""
    return {
        "total_blocks": state.get("total_blocks", 0),
        "block_breakdown": {
            "text": state.get("text_blocks", 0),
            "table": state.get("table_blocks", 0),
            "image": state.get("image_blocks", 0)
        },
        "questions_generated": state.get("questions_generated", 0),
        "keywords_count": len(state.get("keywords", [])),
        "topics_count": len(state.get("main_topics", [])),
        "has_summary": bool(state.get("summary", "")),
        "status": state.get("processing_status", "pending"),
        "processing_time": state.get("processing_time", 0.0)
    }


def is_analysis_successful(state: DocumentAnalyzerState) -> bool:
    """분석 성공 여부"""
    return (state.get("processing_status") == "completed" and 
            state.get("error_message") is None)


def get_text_content(state: DocumentAnalyzerState) -> str:
    """모든 텍스트 콘텐츠 결합"""
    text_parts = []
    blocks = state.get("blocks", [])
    for block in blocks:
        if block.get('type') in ['paragraph', 'heading', 'section']:
            content = block.get('content', '')
            if content:
                text_parts.append(str(content))
    return "\n".join(text_parts)


def get_all_questions(state: DocumentAnalyzerState) -> List[Dict]:
    """모든 생성된 질문 반환"""
    all_questions = []
    blocks = state.get("blocks", [])
    for block in blocks:
        questions = block.get('questions', [])
        all_questions.extend(questions)
    return all_questions


def get_questions_by_type(state: DocumentAnalyzerState, question_type: str) -> List[Dict]:
    """타입별 질문 반환"""
    all_questions = get_all_questions(state)
    return [q for q in all_questions if q.get('type') == question_type]


def create_document_analyzer_state(
    pdf_path: Optional[str] = None,
    collection_name: Optional[str] = None
) -> DocumentAnalyzerState:
    """DocumentAnalyzerState 인스턴스를 생성하는 팩토리 함수"""
    
    from ..base.state import create_base_state
    import uuid
    
    # BaseState 생성
    base_state = create_base_state(
        session_id=str(uuid.uuid4()),
        request_id=str(uuid.uuid4())
    )
    
    # DocumentAnalyzerState 특화 필드 추가
    state = DocumentAnalyzerState(**base_state)
    state.update({
        "pdf_path": pdf_path,
        "collection_name": collection_name,
        "blocks": [],
        "total_blocks": 0,
        "text_blocks": 0,
        "table_blocks": 0,
        "image_blocks": 0,
        "questions_generated": 0,
        "keywords": [],
        "main_topics": [],
        "summary": "",
        "processing_status": "pending",
        "error_message": None,
        "processing_time": 0.0,
        "image_save_dir": ""
    })
    
    return state