# src/pipelines/document_processing/pipeline.py
import datetime
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph

from src.agents.document_analyzer.tools.keyword_summary import (
    extract_keywords_and_summary,
)

# 기존 Agents 코드 import
from src.agents.document_analyzer.tools.unified_parser import parse_pdf_unified
from src.pipelines.base.exceptions import PipelineException
from src.pipelines.base.pipeline import BasePipeline
from src.pipelines.document_processing.state import DocumentProcessingState

# from db.vectordb.client import get_vector_client


class DocumentProcessingPipeline(BasePipeline[DocumentProcessingState]):
    """문서 처리 LangGraph Pipeline"""

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):

        # Pipeline별 기본 설정
        default_config = {
            "max_retries": 3,
            "timeout_seconds": 600,  # 10분
            "enable_vectordb": False,
            "chunk_size": 1000,
            "chunk_overlap": 200,
        }

        # 설정 병합
        final_config = {**default_config, **(config or {})}

        super().__init__(config=final_config, **kwargs)

    def _get_state_schema(self) -> type:
        """Pipeline 상태 스키마 반환"""
        return DocumentProcessingState

    def _get_node_list(self) -> List[str]:
        """노드 목록 반환 (진행률 계산용)"""
        return [
            "parse_document",
            "analyze_content",
            "extract_keywords",
            "store_vectors",
            "finalize",
        ]

    def _build_workflow(self) -> StateGraph:
        """문서 처리 워크플로우 구성"""
        workflow = StateGraph(DocumentProcessingState)
        for node in self._get_node_list():
            node_func = getattr(self, f"_{node}_node", None)
            if node_func:
                workflow.add_node(node, self._create_node_wrapper(node_func))
        workflow.add_node(
            "error_handler", self._create_node_wrapper(self._error_handler_node)
        )
        workflow.set_entry_point(self._get_node_list()[0])

        # 조건부 라우팅 자동화
        for idx, node in enumerate(self._get_node_list()[:-1]):
            next_node = self._get_node_list()[idx + 1]
            workflow.add_conditional_edges(
                node,
                self._route_next_step,
                {next_node: next_node, "error_handler": "error_handler", END: END},
            )
        # 마지막 노드에서 finalize로
        workflow.add_edge(self._get_node_list()[-1], END)
        workflow.add_edge("error_handler", END)
        return workflow

    # ==================== 실행 메서드 ====================

    async def run(
        self, input_data: Dict[str, Any], session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Pipeline 실행"""
        try:
            # 초기 상태 구성
            initial_state = {
                **self.default_state,
                **input_data,
                "started_at": datetime.datetime.now().isoformat(),
            }

            self.logger.info(
                f"Starting document processing for document_id: {input_data.get('document_id')}"
            )
            self.logger.info(
                f"Starting document processing for document_id: {initial_state.get('filename')}"
            )

            # LangGraph 실행
            config = {
                "configurable": {
                    "thread_id": session_id or initial_state["pipeline_id"]
                }
            }
            result = await self.compiled_graph.ainvoke(initial_state, config)

            result["completed_at"] = datetime.datetime.now().isoformat()
            self.logger.info(
                f"Document processing completed: {result.get('processing_status')}"
            )
            return result

        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {str(e)}")
            return {
                **input_data,
                "processing_status": "failed",
                "completed_at": datetime.datetime.now().isoformat(),
            }

    async def stream(
        self, input_data: Dict[str, Any], session_id: Optional[str] = None
    ):
        """Pipeline 스트리밍 실행"""
        initial_state = {
            **self.default_state,
            **input_data,
            "started_at": datetime.datetime.now().isoformat(),
        }

        config = {
            "configurable": {"thread_id": session_id or initial_state["pipeline_id"]}
        }

        async for chunk in self.compiled_graph.astream(initial_state, config):
            yield chunk

    # ==================== 노드 구현 ====================

    async def _parse_document_node(
        self, state: DocumentProcessingState
    ) -> Dict[str, Any]:
        """문서 파싱 노드"""
        self.logger.info(f"Parsing document: {state['document_path']}")

        try:
            # 기존 unified_parser 사용
            blocks = parse_pdf_unified(state["document_path"])

            # 블록 타입별 통계
            text_blocks = [
                b
                for b in blocks
                if b.get("type") in ["paragraph", "section", "heading"]
            ]
            table_blocks = [b for b in blocks if b.get("type") == "table"]
            image_blocks = [b for b in blocks if b.get("type") == "image"]

            self.logger.info(
                f"Parsed {len(blocks)} blocks: {len(text_blocks)} text, {len(table_blocks)} tables, {len(image_blocks)} images"
            )

            return {
                **state,
                "parsed_blocks": blocks,
                "block_statistics": {
                    "total": len(blocks),
                    "text": len(text_blocks),
                    "table": len(table_blocks),
                    "image": len(image_blocks),
                },
                **self._update_progress("parse_document_complete"),
            }

        except Exception as e:
            raise PipelineException(
                message=f"Document parsing failed: {str(e)}",
                pipeline_name=self.pipeline_name,
                step="parse_document",
            )

    async def _analyze_content_node(
        self, state: DocumentProcessingState
    ) -> Dict[str, Any]:
        """내용 분석 노드"""
        self.logger.info("Analyzing document content")

        try:
            blocks = state["parsed_blocks"]

            # 기본 분석 정보 추출
            total_text = ""
            sections = []

            for block in blocks:
                if block.get("type") in ["paragraph", "heading"]:
                    content = block.get("content", "").strip()
                    if content:
                        total_text += content + "\n"

                if block.get("type") == "heading":
                    sections.append(block.get("content", ""))

            # 문서 메타 분석
            analysis_result = {
                "total_characters": len(total_text),
                "total_words": len(total_text.split()),
                "sections_count": len(sections),
                "sections": sections[:10],  # 상위 10개 섹션만
                "avg_block_size": len(total_text) // len(blocks) if blocks else 0,
            }

            self.logger.info(
                f"Content analysis: {analysis_result['total_words']} words, {analysis_result['sections_count']} sections"
            )

            return {
                **state,
                "content_analysis": analysis_result,
                **self._update_progress("analyze_content_complete"),
            }

        except Exception as e:
            raise PipelineException(
                message=f"Content analysis failed: {str(e)}",
                pipeline_name=self.pipeline_name,
                step="analyze_content",
            )

    async def _extract_keywords_node(
        self, state: DocumentProcessingState
    ) -> Dict[str, Any]:
        """키워드 추출 노드"""
        self.logger.info("Extracting keywords and generating summary")

        try:
            blocks = state["parsed_blocks"]
            filename = state["filename"]

            # 기존 extract_keywords_and_summary 함수 사용
            keywords_result = extract_keywords_and_summary(blocks, filename)

            # content_analysis 업데이트
            existing_analysis = state.get("content_analysis", {})
            updated_analysis = {
                **existing_analysis,
                **keywords_result.get("content_analysis", {}),
            }

            self.logger.info(
                f"Keywords extracted: {len(updated_analysis.get('main_topics', []))} topics, {len(updated_analysis.get('key_concepts', []))} concepts"
            )

            return {
                **state,
                "content_analysis": updated_analysis,
                "document_info": keywords_result.get("document_info", {}),
                **self._update_progress("extract_keywords_complete"),
            }

        except Exception as e:
            raise PipelineException(
                message=f"Keyword extraction failed: {str(e)}",
                pipeline_name=self.pipeline_name,
                step="extract_keywords",
            )

    async def _store_vectors_node(
        self, state: DocumentProcessingState
    ) -> Dict[str, Any]:
        """벡터 저장 노드"""
        if not self.config.get("enable_vectordb"):
            self.logger.info("VectorDB storage disabled, skipping")
            return {**state, **self._update_progress("vectors_skipped")}

        self.logger.info("Storing vectors in VectorDB")

        try:
            blocks = state["parsed_blocks"]
            document_id = state["document_id"]
            project_id = state["project_id"]

            # VectorDB 클라이언트 가져오기
            vector_client = get_vector_client()

            # 텍스트 블록만 추출하여 임베딩
            text_blocks = []
            for block in blocks:
                if block.get("type") in ["paragraph", "section", "heading"]:
                    content = block.get("content", "").strip()
                    if content and len(content) > 50:  # 최소 길이 필터
                        text_blocks.append(
                            {
                                "content": content,
                                "type": block.get("type"),
                                "page": block.get("metadata", {}).get("page", 0),
                                "document_id": document_id,
                                "project_id": project_id,
                            }
                        )

            # VectorDB에 저장 (실제 구현은 vector_client에 따라 다름)
            if hasattr(vector_client, "store_document_chunks"):
                await vector_client.store_document_chunks(
                    chunks=text_blocks, document_id=document_id, project_id=project_id
                )

            self.logger.info(f"Stored {len(text_blocks)} text chunks in VectorDB")

            return {
                **state,
                "vector_embeddings": {
                    "chunks_count": len(text_blocks),
                    "status": "stored",
                },
                **self._update_progress("store_vectors_complete"),
            }

        except Exception as e:
            # VectorDB 실패는 전체 Pipeline 실패로 하지 않음
            self.logger.warning(f"VectorDB storage failed: {str(e)}")
            return {
                "vector_embeddings": {
                    "chunks_count": 0,
                    "status": "failed",
                    "error": str(e),
                },
                **self._update_progress("store_vectors_failed"),
            }

    async def _finalize_node(self, state: DocumentProcessingState) -> Dict[str, Any]:
        """최종 정리 노드"""
        self.logger.info("Finalizing document processing")

        return {
            **state,
            **self._update_progress("completed"),
            "processing_status": "completed",
            "completed_at": datetime.datetime.now().isoformat(),
        }

    async def _error_handler_node(
        self, state: DocumentProcessingState
    ) -> Dict[str, Any]:
        """에러 처리 노드"""
        error_message = state.get("error_message", "Unknown error")
        retry_count = state.get("retry_count", 0)
        failed_step = state.get("current_step", "unknown")

        self.logger.error(
            f"Error handler triggered: {error_message} (retry: {retry_count}) at step: {failed_step}"
        )

        # 재시도 가능한지 확인
        if self._should_retry(state):
            self.logger.info(f"Retrying step: {failed_step}")
            return {
                "retry_count": retry_count + 1,
                "processing_status": "retrying",
                "current_step": failed_step,  # 실패한 단계부터 재시작
            }
        else:
            return {
                "processing_status": "failed",
                "error_message": error_message,
                "failed_step": failed_step,
                "completed_at": datetime.datetime.now().isoformat(),
            }
