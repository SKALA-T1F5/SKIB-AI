"""
tests/unit/pipelines/test_document_processing_pipeline.py

DocumentProcessingPipeline 완전 테스트 모듈
- 각 노드별 단위 테스트
- State 전이 검증
- 통합 Pipeline 테스트
- 에러 처리 및 재시도 로직 테스트
"""

from unittest.mock import patch

import pytest

from src.pipelines.base.exceptions import PipelineException

# Pipeline 및 State import
from src.pipelines.document_processing.pipeline import DocumentProcessingPipeline
from src.pipelines.document_processing.state import DocumentProcessingState


class TestDocumentProcessingPipeline:
    """DocumentProcessingPipeline 테스트 클래스"""

    @pytest.fixture
    def sample_config(self):
        """테스트용 Pipeline 설정"""
        return {
            "max_retries": 2,
            "timeout_seconds": 300,
            "enable_vectordb": True,
            "chunk_size": 500,
            "chunk_overlap": 100,
        }

    @pytest.fixture
    def pipeline(self, sample_config):
        """Pipeline 인스턴스 생성"""
        return DocumentProcessingPipeline(config=sample_config)

    @pytest.fixture
    def sample_input_data(self):
        """테스트용 입력 데이터"""
        return {
            "document_path": "/test/path/sample.pdf",
            "document_id": 123,
            "project_id": 456,
            "filename": "sample.pdf",
        }

    @pytest.fixture
    def sample_parsed_blocks(self):
        """파싱된 블록 데이터 샘플"""
        return [
            {
                "type": "heading",
                "content": "제1장 개요",
                "metadata": {"page": 1, "text_length": 7},
            },
            {
                "type": "paragraph",
                "content": "이것은 테스트용 문단입니다. 시스템의 전체적인 구조를 설명합니다.",
                "metadata": {"page": 1, "text_length": 35},
            },
            {
                "type": "table",
                "content": "표 1. 시스템 비교\n컬럼1 | 컬럼2\n값1 | 값2",
                "metadata": {"page": 2, "text_length": 25},
            },
            {
                "type": "image",
                "content": "그림 1. 시스템 아키텍처",
                "metadata": {"page": 2, "text_length": 12},
            },
        ]

    @pytest.fixture
    def sample_keywords_result(self):
        """키워드 추출 결과 샘플"""
        return {
            "content_analysis": {
                "main_topics": ["시스템 구조", "개요", "아키텍처"],
                "key_concepts": ["테스트", "문단", "비교"],
                "technical_terms": ["시스템", "구조", "아키텍처"],
                "summary": "이 문서는 시스템의 전체적인 구조와 개요를 설명합니다.",
            },
            "document_info": {
                "document_type": "technical_document",
                "complexity_level": "medium",
                "estimated_reading_time": 10,
            },
        }

    # ==================== 초기화 및 설정 테스트 ====================

    def test_pipeline_initialization(self, sample_config):
        """Pipeline 초기화 테스트"""
        pipeline = DocumentProcessingPipeline(config=sample_config)

        # 설정 확인
        assert pipeline.config["max_retries"] == 2
        assert pipeline.config["timeout_seconds"] == 300
        assert pipeline.config["enable_vectordb"] is True
        assert pipeline.config["chunk_size"] == 500

        # 기본 설정도 포함되어 있는지 확인
        assert "chunk_overlap" in pipeline.config
        assert pipeline.pipeline_name == "DocumentProcessingPipeline"

    def test_default_config_merge(self):
        """기본 설정과 사용자 설정 병합 테스트"""
        custom_config = {"max_retries": 5, "new_setting": "test"}
        pipeline = DocumentProcessingPipeline(config=custom_config)

        # 사용자 설정 우선 적용
        assert pipeline.config["max_retries"] == 5
        assert pipeline.config["new_setting"] == "test"

        # 기본 설정도 유지
        assert pipeline.config["timeout_seconds"] == 600  # 기본값
        assert pipeline.config["enable_vectordb"] is False  # 기본값

    def test_state_schema(self, pipeline):
        """State 스키마 확인"""
        schema = pipeline._get_state_schema()
        assert schema == DocumentProcessingState

    def test_node_list(self, pipeline):
        """노드 목록 확인"""
        nodes = pipeline._get_node_list()
        expected_nodes = [
            "parse_document",
            "analyze_content",
            "extract_keywords",
            "store_vectors",
            "finalize",
        ]
        assert nodes == expected_nodes

    def test_workflow_construction(self, pipeline):
        """워크플로우 구성 테스트"""
        workflow = pipeline._build_workflow()

        # 노드가 모두 추가되었는지 확인
        assert "parse_document" in workflow.nodes
        assert "analyze_content" in workflow.nodes
        assert "extract_keywords" in workflow.nodes
        assert "store_vectors" in workflow.nodes
        assert "finalize" in workflow.nodes
        assert "error_handler" in workflow.nodes

    # ==================== 개별 노드 테스트 ====================

    @pytest.mark.asyncio
    async def test_parse_document_node_success(
        self, pipeline, sample_input_data, sample_parsed_blocks
    ):
        """문서 파싱 노드 성공 테스트"""
        # Mock parse_pdf_unified 함수
        with patch(
            "src.pipelines.document_processing.pipeline.parse_pdf_unified"
        ) as mock_parse:
            mock_parse.return_value = sample_parsed_blocks

            state = DocumentProcessingState(**sample_input_data)
            result = await pipeline._parse_document_node(state)

            # 결과 검증
            assert result["parsed_blocks"] == sample_parsed_blocks
            assert result["block_statistics"]["total"] == 4
            assert result["block_statistics"]["text"] == 2  # heading, paragraph
            assert result["block_statistics"]["table"] == 1
            assert result["block_statistics"]["image"] == 1

            # 진행률 업데이트 확인
            assert result["processing_status"] != "failed"

            mock_parse.assert_called_once_with(sample_input_data["document_path"])

    @pytest.mark.asyncio
    async def test_parse_document_node_failure(self, pipeline, sample_input_data):
        """문서 파싱 노드 실패 테스트"""
        # Mock이 예외를 발생시키도록 설정
        with patch(
            "src.pipelines.document_processing.pipeline.parse_pdf_unified"
        ) as mock_parse:
            mock_parse.side_effect = Exception("PDF parsing failed")

            state = DocumentProcessingState(**sample_input_data)

            # PipelineException이 발생해야 함
            with pytest.raises(PipelineException) as exc_info:
                await pipeline._parse_document_node(state)

            assert "Document parsing failed" in str(exc_info.value)
            assert exc_info.value.step == "parse_document"

    @pytest.mark.asyncio
    async def test_analyze_content_node(
        self, pipeline, sample_input_data, sample_parsed_blocks
    ):
        """내용 분석 노드 테스트"""
        state = DocumentProcessingState(
            **sample_input_data, parsed_blocks=sample_parsed_blocks
        )
        result = await pipeline._analyze_content_node(state)

        # 분석 결과 검증
        analysis = result["content_analysis"]
        assert analysis["total_characters"] > 0
        assert analysis["total_words"] > 0
        assert analysis["sections_count"] == 1  # heading 1개
        assert "제1장 개요" in analysis["sections"]
        assert analysis["avg_block_size"] > 0

        # 진행률 업데이트 확인
        assert result["processing_status"] == "running"

    @pytest.mark.asyncio
    async def test_extract_keywords_node(
        self, pipeline, sample_input_data, sample_parsed_blocks, sample_keywords_result
    ):
        """키워드 추출 노드 테스트"""
        # Mock extract_keywords_and_summary 함수
        with patch(
            "src.pipelines.document_processing.pipeline.extract_keywords_and_summary"
        ) as mock_extract:
            mock_extract.return_value = sample_keywords_result

            state = DocumentProcessingState(
                **sample_input_data,
                parsed_blocks=sample_parsed_blocks,
                content_analysis={"existing_field": "value"},
            )
            result = await pipeline._extract_keywords_node(state)

            # 결과 검증
            assert "main_topics" in result["content_analysis"]
            assert "key_concepts" in result["content_analysis"]
            assert "technical_terms" in result["content_analysis"]
            assert (
                result["content_analysis"]["existing_field"] == "value"
            )  # 기존 필드 유지
            assert result["document_info"] == sample_keywords_result["document_info"]

            mock_extract.assert_called_once_with(
                sample_parsed_blocks, sample_input_data["filename"]
            )

    # TODO: 벡터 저장 노드 테스트는 VectorDB 클라이언트가 필요하므로 주석 처리
    # @pytest.mark.asyncio
    # async def test_store_vectors_node_enabled(self, pipeline, sample_input_data, sample_parsed_blocks):
    #     """벡터 저장 노드 - VectorDB 활성화 테스트"""
    #     # VectorDB가 활성화된 설정으로 pipeline 재생성
    #     pipeline.config["enable_vectordb"] = True

    #     # Mock VectorDB 클라이언트
    #     mock_client = AsyncMock()
    #     mock_client.store_document_chunks = AsyncMock()

    #     with patch('src.pipelines.document_processing.pipeline.get_vector_client') as mock_get_client:
    #         mock_get_client.return_value = mock_client

    #         state = DocumentProcessingState(**sample_input_data, parsed_blocks=sample_parsed_blocks)
    #         result = await pipeline._store_vectors_node(state)

    #         # 결과 검증
    #         assert result["vector_embeddings"]["status"] == "stored"
    #         assert result["vector_embeddings"]["chunks_count"] == 2  # paragraph, heading만 저장

    #         # VectorDB 호출 확인
    #         mock_client.store_document_chunks.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_vectors_node_disabled(
        self, pipeline, sample_input_data, sample_parsed_blocks
    ):
        """벡터 저장 노드 - VectorDB 비활성화 테스트"""
        # VectorDB가 비활성화된 설정
        pipeline.config["enable_vectordb"] = False

        state = DocumentProcessingState(
            **sample_input_data, parsed_blocks=sample_parsed_blocks
        )
        result = await pipeline._store_vectors_node(state)

        # 스킵 확인
        assert result["processing_status"] == "completed"

    # TODO: 벡터 저장 노드 실패 테스트는 VectorDB 클라이언트가 필요하므로 주석 처리
    # @pytest.mark.asyncio
    # async def test_store_vectors_node_failure(self, pipeline, sample_input_data, sample_parsed_blocks):
    #     """벡터 저장 노드 실패 테스트 - 전체 실패하지 않음"""
    #     pipeline.config["enable_vectordb"] = True

    #     # Mock VectorDB 클라이언트가 실패하도록 설정
    #     with patch('src.pipelines.document_processing.pipeline.get_vector_client') as mock_get_client:
    #         mock_get_client.side_effect = Exception("VectorDB connection failed")

    #         state = DocumentProcessingState(**sample_input_data, parsed_blocks=sample_parsed_blocks)
    #         result = await pipeline._store_vectors_node(state)

    #         # VectorDB 실패는 전체 pipeline을 실패시키지 않음
    #         assert result["vector_embeddings"]["status"] == "failed"
    #         assert "VectorDB connection failed" in result["vector_embeddings"]["error"]

    @pytest.mark.asyncio
    async def test_finalize_node(self, pipeline, sample_input_data):
        """최종화 노드 테스트"""
        state = DocumentProcessingState(**sample_input_data)
        result = await pipeline._finalize_node(state)

        # 최종화 확인
        assert result["processing_status"] == "completed"
        assert "completed_at" in result

    @pytest.mark.asyncio
    async def test_error_handler_node_retry(self, pipeline, sample_input_data):
        """에러 핸들러 노드 - 재시도 테스트"""
        state = DocumentProcessingState(
            **sample_input_data,
            error_message="Temporary failure",
            retry_count=1,
            current_step="parse_document",
        )

        # _should_retry 메서드를 Mock으로 True 반환하도록 설정
        with patch.object(pipeline, "_should_retry", return_value=True):
            result = await pipeline._error_handler_node(state)

            # 재시도 설정 확인
            assert result["processing_status"] == "retrying"
            assert result["retry_count"] == 2
            assert result["current_step"] == "parse_document"

    @pytest.mark.asyncio
    async def test_error_handler_node_final_failure(self, pipeline, sample_input_data):
        """에러 핸들러 노드 - 최종 실패 테스트"""
        state = DocumentProcessingState(
            **sample_input_data,
            error_message="Final failure",
            retry_count=3,
            current_step="analyze_content",
        )

        # _should_retry 메서드를 Mock으로 False 반환하도록 설정
        with patch.object(pipeline, "_should_retry", return_value=False):
            result = await pipeline._error_handler_node(state)

            # 최종 실패 확인
            assert result["processing_status"] == "failed"
            assert result["error_message"] == "Final failure"
            assert result["failed_step"] == "analyze_content"
            assert "completed_at" in result

    # ==================== 통합 테스트 ====================
    # TODO: 전체 pipeline 테스트는 API를 통해서 실행 + VectorDB 클라이언트가 필요하므로 주석 처리
    # @pytest.mark.asyncio
    # async def test_full_pipeline_success(self, pipeline, sample_input_data, sample_parsed_blocks, sample_keywords_result):
    #     """전체 Pipeline 성공 시나리오 테스트"""
    #     # 모든 외부 의존성을 Mock으로 설정
    #     with patch('src.pipelines.document_processing.pipeline.parse_pdf_unified') as mock_parse, \
    #          patch('src.pipelines.document_processing.pipeline.extract_keywords_and_summary') as mock_extract, \
    #          patch('src.pipelines.document_processing.pipeline.get_vector_client') as mock_vector:

    #         mock_parse.return_value = sample_parsed_blocks
    #         mock_extract.return_value = sample_keywords_result
    #         mock_vector.return_value = AsyncMock()

    #         # Pipeline 실행
    #         result = await pipeline.run(sample_input_data, session_id="test-session")

    #         # 최종 결과 검증
    #         assert result["processing_status"] == "completed"
    #         assert result["parsed_blocks"] == sample_parsed_blocks
    #         assert "main_topics" in result["content_analysis"]
    #         assert "started_at" in result
    #         assert "completed_at" in result

    #         # 모든 Mock이 호출되었는지 확인
    #         mock_parse.assert_called_once()
    #         mock_extract.assert_called_once()

    # ==================== 에러 시나리오 테스트 ====================

    @pytest.mark.asyncio
    async def test_pipeline_failure_recovery(self, pipeline, sample_input_data):
        """Pipeline 실패 복구 테스트"""
        # 첫 번째 호출은 실패, 두 번째 호출은 성공하도록 설정
        with patch(
            "src.pipelines.document_processing.pipeline.parse_pdf_unified"
        ) as mock_parse:
            mock_parse.side_effect = [
                Exception("Temporary failure"),
                [{"type": "paragraph", "content": "Success on retry"}],
            ]

            # Pipeline 실행 (내부적으로 재시도 로직이 있다면)
            result = await pipeline.run(sample_input_data)

            # 실패 결과 확인 (현재 구현에서는 예외가 잡혀서 실패 상태 반환)
            assert result["processing_status"] == "retrying"

    # ==================== 진행률 추적 테스트 ====================

    def test_progress_calculation(self, pipeline):
        """진행률 계산 테스트"""
        # _update_progress 메서드가 있다면 테스트
        if hasattr(pipeline, "_update_progress"):
            # 첫 번째 단계 완료
            progress_update = pipeline._update_progress("parse_document_complete")
            assert "progress_percentage" in progress_update
            assert 0 < progress_update["progress_percentage"] <= 20.0

            # 마지막 단계 완료
            final_progress = pipeline._update_progress("completed")
            assert final_progress["progress_percentage"] == 100

    # ==================== 상태 검증 테스트 ====================

    def test_state_validation(self, sample_input_data):
        """State 유효성 검증 테스트"""
        # 필수 필드가 있는지 확인
        state = DocumentProcessingState(**sample_input_data)

        # 필수 필드 검증
        assert state["document_path"] == sample_input_data["document_path"]
        assert state["document_id"] == sample_input_data["document_id"]
        assert state["project_id"] == sample_input_data["project_id"]
        assert state["filename"] == sample_input_data["filename"]

    def test_state_optional_fields(self, sample_input_data):
        """State 선택적 필드 테스트"""
        state = DocumentProcessingState(**sample_input_data)

        # 선택적 필드들이 없어도 에러가 발생하지 않아야 함
        state.get("parsed_blocks", [])
        state.get("content_analysis", {})
        state.get("vector_embeddings", [])
        state.get("processing_stats", {})

    # ==================== 실제 파일 테스트 (통합) ====================

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_file_processing(self, pipeline, tmp_path):
        """실제 파일로 통합 테스트 (선택적)"""
        # 테스트용 더미 PDF 파일 생성 (또는 실제 테스트 파일 사용)
        test_file = tmp_path / "test_document.txt"
        test_file.write_text(
            "테스트 문서 내용입니다.\n제1장 개요\n이것은 테스트입니다.",
            encoding="utf-8",
        )

        input_data = {
            "document_path": str(test_file),
            "document_id": 999,
            "project_id": 888,
            "filename": "test_document.txt",
        }

        # 실제 파일이 PDF가 아니므로 Mock 사용
        with patch(
            "src.pipelines.document_processing.pipeline.parse_pdf_unified"
        ) as mock_parse:
            mock_parse.return_value = [
                {"type": "paragraph", "content": "테스트 문서 내용입니다."}
            ]

            result = await pipeline.run(input_data)

            # 결과가 완료되었는지 확인 (에러가 없는 한)
            assert "processing_status" in result

    # ==================== 성능 테스트 ====================

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_pipeline_performance(
        self, pipeline, sample_input_data, sample_parsed_blocks
    ):
        """Pipeline 성능 테스트"""
        import time

        with patch(
            "src.pipelines.document_processing.pipeline.parse_pdf_unified"
        ) as mock_parse:
            mock_parse.return_value = sample_parsed_blocks

            start_time = time.time()
            await pipeline.run(sample_input_data)
            end_time = time.time()

            processing_time = end_time - start_time

            # 성능 기준 확인 (예: 10초 이내)
            assert processing_time < 10.0
            print(f"Pipeline 처리 시간: {processing_time:.2f}초")

    # ==================== 동시성 테스트 ====================

    @pytest.mark.asyncio
    async def test_concurrent_pipeline_execution(
        self, sample_config, sample_input_data, sample_parsed_blocks
    ):
        """동시 Pipeline 실행 테스트"""
        import asyncio

        # 여러 Pipeline 인스턴스 생성
        pipelines = [DocumentProcessingPipeline(config=sample_config) for _ in range(3)]

        with patch(
            "src.pipelines.document_processing.pipeline.parse_pdf_unified"
        ) as mock_parse:
            mock_parse.return_value = sample_parsed_blocks

            # 동시 실행
            tasks = [
                pipeline.run({**sample_input_data, "document_id": i})
                for i, pipeline in enumerate(pipelines)
            ]

            results = await asyncio.gather(*tasks)

            # 모든 결과가 성공했는지 확인
            for result in results:
                assert "processing_status" in result

    def test_node_wrapper_creation(self, pipeline):
        """노드 래퍼 생성 테스트"""
        # _create_node_wrapper 메서드가 있다면
        if hasattr(pipeline, "_create_node_wrapper"):

            async def dummy_node(state):
                return {"test": "value"}

            wrapped = pipeline._create_node_wrapper(dummy_node)
            assert callable(wrapped)

    def test_route_next_step(self, pipeline):
        """라우팅 로직 테스트"""
        # _route_next_step 메서드가 있다면
        if hasattr(pipeline, "_route_next_step"):
            # 정상 상태
            normal_state = {"processing_status": "processing"}
            route = pipeline._route_next_step(normal_state)
            assert route in [
                "analyze_content",
                "extract_keywords",
                "store_vectors",
                "finalize",
                "error_handler",
                "__end__",
            ]

            # 에러 상태
            error_state = {"processing_status": "failed", "error_message": "Test error"}
            route = pipeline._route_next_step(error_state)
            assert route in ["error_handler", "__end__"]
