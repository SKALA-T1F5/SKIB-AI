from typing import Any, Dict, List, Optional

from src.pipelines.base.state import BasePipelineState


class DocumentProcessingState(BasePipelineState, total=False):
    """문서 처리 Pipeline 상태"""

    # 문서 관련
    document_path: str
    document_id: int
    project_id: int
    filename: str

    # 처리 결과
    parsed_blocks: List[Dict[str, Any]]
    content_analysis: Dict[str, Any]
    vector_embeddings: List[Dict[str, Any]]
    # 처리 결과
    extracted_content: Optional[Dict[str, Any]]
    document_metadata: Optional[Dict[str, Any]]
    processed_chunks: Optional[List[Dict[str, Any]]]
    vector_storage_result: Optional[Dict[str, Any]]

    # 처리 통계
    processing_stats: Optional[Dict[str, Any]]
