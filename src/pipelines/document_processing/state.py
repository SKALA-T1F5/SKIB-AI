import operator
from typing import Annotated, Any, Dict, List, Optional

from src.pipelines.base.state import BasePipelineState


class DocumentProcessingState(BasePipelineState, total=False):
    """문서 처리 Pipeline 상태 - 각 단계별 출력물 정의"""

    # ==================== 입력 데이터 (초기 설정) ====================
    document_path: str  # 문서 파일 경로
    document_id: int  # 문서 ID
    project_id: int  # 프로젝트 ID
    filename: str  # 파일명

    # ==================== 1단계: parse_document 출력 ====================
    parsed_blocks: List[Dict[str, Any]]  # 파싱된 문서 블록들
    block_statistics: Dict[str, Any]  # 블록 통계 정보
    # 예시: {
    #   "total": 50,
    #   "text": 35,
    #   "table": 10,
    #   "image": 5
    # }

    # ==================== 2단계: analyze_content 출력 ====================
    content_analysis: Dict[str, Any]  # 내용 분석 결과
    # 예시: {
    #   "total_characters": 15000,
    #   "total_words": 2500,
    #   "sections_count": 12,
    #   "sections": ["Introduction", "Methodology", ...],
    #   "avg_block_size": 300
    # }

    # ==================== 3단계: extract_keywords 출력 ====================
    document_info: Dict[str, Any]  # 문서 메타 정보
    # content_analysis가 키워드 추출 결과로 업데이트됨
    # 업데이트된 content_analysis 예시: {
    #   ... (기존 분석 결과),
    #   "main_topics": ["AI", "Machine Learning", ...],
    #   "key_concepts": ["neural networks", "deep learning", ...],
    #   "summary": "This document discusses...",
    #   "document_type": "research_paper"
    # }

    # ==================== 4단계: store_vectors 출력 ====================
    vector_embeddings: Dict[str, Any]  # 벡터 저장 결과
    # 예시: {
    #   "status": "completed",
    #   "collection_name": "my_document_collection",
    #   "uploaded_count": 25,
    #   "total_blocks": 50,
    #   "chunks_count": 25,
    #   "source_file": "document.pdf",
    #   "collection_total": 100
    # }

    # ==================== 5단계: finalize 출력 ====================
    processing_summary: Dict[str, Any]  # 최종 처리 요약
    # 예시: {
    #   "total_processing_time": "00:02:45",
    #   "successful_steps": ["parse", "analyze", "keywords", "vectors"],
    #   "failed_steps": [],
    #   "final_status": "completed"
    # }

    # ==================== 문서 처리 전용 에러 핸들링 ====================
    failed_step: Optional[str]  # 실패한 단계명
    should_retry: bool  # 재시도 여부

    # ==================== 로깅 및 추적 (누적) ====================
    processing_logs: Annotated[List[str], operator.add]  # 처리 로그 (자동 누적)
    error_logs: Annotated[List[str], operator.add]  # 에러 로그 (자동 누적)
    step_results: Annotated[List[Dict[str, Any]], operator.add]  # 각 단계별 결과 요약

    # ==================== 문서 처리 전용 시간 추적 ====================
    step_timestamps: Dict[str, str]  # 각 단계별 타임스탬프
    last_completed_step: Optional[str]  # 마지막 완료된 단계
