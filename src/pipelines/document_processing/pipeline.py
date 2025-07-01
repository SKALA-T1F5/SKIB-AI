import datetime
import os
import traceback
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph

from api.document.schemas.document_status import DocumentProcessingStatus
from api.websocket.services.springboot_notifier import notify_document_progress
from db.vectorDB.chromaDB.pipeline import ChromaDBPipeline
from src.agents.document_analyzer.tools.keyword_summary import (
    extract_keywords_and_summary,
)
from src.agents.document_analyzer.tools.unified_parser import parse_pdf_unified
from src.pipelines.base.exceptions import PipelineException
from src.pipelines.base.pipeline import BasePipeline
from src.pipelines.document_processing.state import DocumentProcessingState
from utils.naming import filename_to_collection


def extract_metadata(state: DocumentProcessingState) -> Dict[str, Any]:
    return {
        "filename": state.get(
            "filename", os.path.basename(state.get("document_path", ""))
        ),
        "documentId": state.get("documentId"),
        "project_id": state.get("project_id"),
    }


def safe_filename_to_collection(state: DocumentProcessingState) -> str:
    metadata = extract_metadata(state)
    base_filename = os.path.splitext(metadata["filename"])[0]
    return filename_to_collection(base_filename)


class DocumentProcessingPipeline(BasePipeline[DocumentProcessingState]):
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        default_config = {
            "max_retries": 3,
            "timeout_seconds": 600,
            "enable_vectordb": False,
            "chunk_size": 1000,
            "chunk_overlap": 200,
        }
        final_config = {**default_config, **(config or {})}
        super().__init__(config=final_config, **kwargs)

    def _get_state_schema(self) -> type:
        return DocumentProcessingState

    def _get_node_list(self) -> List[str]:
        return [
            "parse_document",
            "analyze_content",
            "extract_keywords",
            "store_vectors",
            "finalize",
        ]

    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(DocumentProcessingState)
        for node in self._get_node_list():
            node_func = getattr(self, f"_{node}_node", None)
            if node_func:
                workflow.add_node(node, self._create_node_wrapper(node_func))

        workflow.add_node(
            "error_handler", self._create_node_wrapper(self._error_handler_node)
        )
        workflow.set_entry_point(self._get_node_list()[0])

        for idx, node in enumerate(self._get_node_list()[:-1]):
            next_node = self._get_node_list()[idx + 1]
            workflow.add_conditional_edges(
                node,
                self._route_next_step,
                {next_node: next_node, "error_handler": "error_handler", END: END},
            )

        workflow.add_edge(self._get_node_list()[-1], END)
        workflow.add_edge("error_handler", END)
        return workflow

    async def run(
        self, input_data: Dict[str, Any], session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            initial_state = {
                **self.default_state,
                **input_data,
                "started_at": datetime.datetime.now().isoformat(),
            }
            self.logger.info(
                f"Starting document processing for documentId: {initial_state.get('documentId')}"
            )
            self.logger.info(f"Filename: {initial_state.get('filename')}")

            # 전처리 시작 알림
            await notify_document_progress(
                task_id=self.config.get("task_id"),
                document_id=initial_state.get("documentId"),
                status=DocumentProcessingStatus.PREPROCESSING_START,
            )

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
                "error_type": type(e).__name__,
                "error_trace": traceback.format_exc(),
            }

    async def _parse_document_node(
        self, state: DocumentProcessingState
    ) -> Dict[str, Any]:
        self.logger.info(f"Parsing document: {state['document_path']}")

        # 문서 파싱 시작 알림
        await notify_document_progress(
            task_id=self.config.get("task_id"),
            document_id=state.get("documentId"),
            status=DocumentProcessingStatus.PARSING_DOCUMENT,
        )
        try:
            blocks = parse_pdf_unified(state["document_path"])
            text_blocks = [
                b
                for b in blocks
                if b.get("type") in ["paragraph", "section", "heading"]
            ]
            table_blocks = [b for b in blocks if b.get("type") == "table"]
            image_blocks = [b for b in blocks if b.get("type") == "image"]

            return {
                "parsed_blocks": blocks,
                "filename": extract_metadata(state)["filename"],
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
                message=f"[{self.pipeline_name}:parse_document] {str(e)}",
                pipeline_name=self.pipeline_name,
                step="parse_document",
            )

    async def _analyze_content_node(
        self, state: DocumentProcessingState
    ) -> Dict[str, Any]:
        # 문서 분석 시작 알림
        await notify_document_progress(
            task_id=self.config.get("task_id"),
            document_id=state.get("documentId"),
            status=DocumentProcessingStatus.ANALYZING_CONTENT,
        )
        try:
            blocks = state["parsed_blocks"]
            total_text, sections = "", []

            for block in blocks:
                if block.get("type") in ["paragraph", "heading"]:
                    content = block.get("content", "").strip()
                    if content:
                        total_text += content + "\n"
                if block.get("type") == "heading":
                    sections.append(block.get("content", ""))

            analysis_result = {
                "total_characters": len(total_text),
                "total_words": len(total_text.split()),
                "sections_count": len(sections),
                "sections": sections[:10],
                "avg_block_size": len(total_text) // len(blocks) if blocks else 0,
            }

            return {
                "content_analysis": analysis_result,
                **self._update_progress("analyze_content_complete"),
            }

        except Exception as e:
            raise PipelineException(
                message=f"[{self.pipeline_name}:analyze_content] {str(e)}",
                pipeline_name=self.pipeline_name,
                step="analyze_content",
            )

    async def _extract_keywords_node(
        self, state: DocumentProcessingState
    ) -> Dict[str, Any]:
        # 요약 시작 알림
        await notify_document_progress(
            task_id=self.config.get("task_id"),
            document_id=state.get("documentId"),
            status=DocumentProcessingStatus.SUMMARIZING,
        )
        try:
            blocks = state["parsed_blocks"]
            filename = extract_metadata(state)["filename"]
            keywords_result = extract_keywords_and_summary(blocks, filename)
            updated_analysis = {
                **state.get("content_analysis", {}),
                **keywords_result.get("content_analysis", {}),
            }

            return {
                "content_analysis": updated_analysis,
                "document_info": keywords_result.get("document_info", {}),
                **self._update_progress("extract_keywords_complete"),
            }

        except Exception as e:
            raise PipelineException(
                message=f"[{self.pipeline_name}:extract_keywords] {str(e)}",
                pipeline_name=self.pipeline_name,
                step="extract_keywords",
            )

    async def _store_vectors_node(
        self, state: DocumentProcessingState
    ) -> Dict[str, Any]:
        # 벡터 저장 시작 알림
        await notify_document_progress(
            task_id=self.config.get("task_id"),
            document_id=state.get("documentId"),
            status=DocumentProcessingStatus.STORING_VECTORDB,
        )
        try:
            if not self.config.get("enable_vectordb", True):
                return {
                    "vector_embeddings": {
                        "status": "skipped",
                        "reason": "vectordb_disabled",
                        "chunks_count": 0,
                    },
                    **self._update_progress("store_vectors_complete"),
                }

            parsed_blocks = state.get("parsed_blocks", [])
            if not parsed_blocks:
                return {
                    "vector_embeddings": {
                        "status": "skipped",
                        "reason": "no_blocks",
                        "chunks_count": 0,
                    },
                    **self._update_progress("store_vectors_complete"),
                }

            collection_name = safe_filename_to_collection(state)
            filename = extract_metadata(state)["filename"]

            chromadb_pipeline = ChromaDBPipeline()
            upload_result = chromadb_pipeline.process_and_upload_document(
                document_blocks=parsed_blocks,
                collection_name=collection_name,
                source_file=filename,
                recreate_collection=False,
            )

            uploaded_count = upload_result.get("uploaded_count", 0)

            return {
                "vector_embeddings": {
                    "status": upload_result.get("status", "completed"),
                    "collection_name": collection_name,
                    "uploaded_count": uploaded_count,
                    "total_blocks": len(parsed_blocks),
                    "chunks_count": uploaded_count,
                    "source_file": filename,
                    "collection_total": upload_result.get(
                        "collection_total", uploaded_count
                    ),
                },
                **self._update_progress("store_vectors_complete"),
            }

        except Exception as e:
            return {
                "vector_embeddings": {
                    "chunks_count": 0,
                    "status": "failed",
                    "error": str(e),
                },
                **self._update_progress("store_vectors_failed"),
            }

    async def _finalize_node(self, state: DocumentProcessingState) -> Dict[str, Any]:
        return {
            **self._update_progress("completed"),
            "processing_status": "completed",
            "completed_at": datetime.datetime.now().isoformat(),
        }

    async def _error_handler_node(
        self, state: DocumentProcessingState
    ) -> Dict[str, Any]:
        error_message = state.get("error_message", "Unknown error")
        retry_count = state.get("retry_count", 0)
        failed_step = state.get("current_step", "unknown")

        self.logger.error(
            f"Error handler triggered: {error_message} (retry: {retry_count}) at step: {failed_step}"
        )

        if self._should_retry(state):
            return {
                "retry_count": retry_count + 1,
                "processing_status": "retrying",
                "current_step": failed_step,
            }
        else:
            return {
                "processing_status": "failed",
                "error_message": error_message,
                "failed_step": failed_step,
                "completed_at": datetime.datetime.now().isoformat(),
            }
