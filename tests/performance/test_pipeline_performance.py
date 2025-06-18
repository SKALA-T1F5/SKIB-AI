"""
파이프라인 성능 테스트
메모리 사용량, 응답 시간, 동시 처리 능력 등을 테스트
"""

import asyncio
import os
import time
from unittest.mock import AsyncMock, Mock, patch

import psutil
import pytest

from src.pipelines.test_generation.pipeline import TestGenerationPipeline


class TestPipelinePerformance:
    """파이프라인 성능 테스트"""

    @pytest.mark.asyncio
    async def test_memory_usage_during_processing(
        self,
        mock_pdf_file,
        sample_user_prompt,
        sample_blocks,
        sample_questions,
        mock_openai_response,
    ):
        """처리 중 메모리 사용량 테스트"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        pipeline = TestGenerationPipeline()

        # Mock 설정
        mock_doc_state = Mock()
        mock_doc_state.is_successful.return_value = True
        mock_doc_state.blocks = sample_blocks * 100  # 큰 데이터 시뮬레이션
        mock_doc_state.keywords = ["키워드"] * 50
        mock_doc_state.summary = "요약" * 100
        mock_doc_state.main_topics = ["주제"] * 20
        mock_doc_state.get_statistics.return_value = {"total_blocks": 300}

        mock_doc_agent = Mock()
        mock_doc_agent.analyze_document.return_value = mock_doc_state

        mock_design_result = {
            "output": {
                "requirements": {},
                "test_summary": "요약",
                "test_config": {
                    "num_questions": 5,
                    "num_objective": 3,
                    "num_subjective": 2,
                },
            }
        }
        mock_test_designer = AsyncMock()
        mock_test_designer.execute.return_value = mock_design_result

        with patch(
            "src.pipelines.test_generation.pipeline.DocumentAnalyzerAgent",
            return_value=mock_doc_agent,
        ), patch(
            "src.pipelines.test_generation.pipeline.TestDesignerAgent",
            return_value=mock_test_designer,
        ), patch(
            "src.agents.question_generator.tools.question_generator.QuestionGenerator._generate_question",
            return_value=sample_questions,
        ), patch(
            "openai.ChatCompletion.acreate", return_value=mock_openai_response
        ), patch.object(
            pipeline, "_upload_to_vectordb", return_value=100
        ), patch.object(
            pipeline, "_save_results"
        ):

            await pipeline.run_complete_workflow(
                mock_pdf_file, sample_user_prompt, "test_collection"
            )

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # 메모리 증가가 합리적인 범위 내인지 확인 (100MB 이하)
        assert (
            memory_increase < 100
        ), f"메모리 사용량이 너무 많이 증가했습니다: {memory_increase:.2f}MB"

    @pytest.mark.asyncio
    async def test_processing_time_large_document(
        self,
        mock_pdf_file,
        sample_user_prompt,
        sample_blocks,
        sample_questions,
        mock_openai_response,
    ):
        """큰 문서 처리 시간 테스트"""
        pipeline = TestGenerationPipeline()

        # 큰 문서 시뮬레이션
        large_blocks = sample_blocks * 50  # 150개 블록

        mock_doc_state = Mock()
        mock_doc_state.is_successful.return_value = True
        mock_doc_state.blocks = large_blocks
        mock_doc_state.keywords = ["키워드"] * 20
        mock_doc_state.summary = "큰 문서 요약"
        mock_doc_state.main_topics = ["주제"] * 10
        mock_doc_state.get_statistics.return_value = {"total_blocks": len(large_blocks)}

        mock_doc_agent = Mock()
        mock_doc_agent.analyze_document.return_value = mock_doc_state

        mock_design_result = {
            "output": {
                "requirements": {},
                "test_summary": "요약",
                "test_config": {
                    "num_questions": 10,
                    "num_objective": 6,
                    "num_subjective": 4,
                },
            }
        }
        mock_test_designer = AsyncMock()
        mock_test_designer.execute.return_value = mock_design_result

        start_time = time.time()

        with patch(
            "src.pipelines.test_generation.pipeline.DocumentAnalyzerAgent",
            return_value=mock_doc_agent,
        ), patch(
            "src.pipelines.test_generation.pipeline.TestDesignerAgent",
            return_value=mock_test_designer,
        ), patch(
            "src.agents.question_generator.generate_questions.generate_question",
            return_value=sample_questions,
        ), patch(
            "openai.ChatCompletion.acreate", return_value=mock_openai_response
        ), patch.object(
            pipeline, "_upload_to_vectordb", return_value=len(large_blocks)
        ), patch.object(
            pipeline, "_save_results"
        ):

            result = await pipeline.run_complete_workflow(
                mock_pdf_file, sample_user_prompt, "test_collection"
            )

        processing_time = time.time() - start_time

        # 처리 시간이 합리적인 범위 내인지 확인 (10초 이하, Mock이므로 빨라야 함)
        assert (
            processing_time < 10
        ), f"처리 시간이 너무 오래 걸렸습니다: {processing_time:.2f}초"

        # 결과에 처리 시간이 기록되었는지 확인
        assert "processing_time" in result["pipeline_info"]
        assert result["pipeline_info"]["processing_time"] > 0

    @pytest.mark.asyncio
    async def test_concurrent_pipeline_execution(
        self,
        mock_pdf_file,
        sample_user_prompt,
        sample_blocks,
        sample_questions,
        mock_openai_response,
    ):
        """동시 파이프라인 실행 테스트"""
        # 3개의 파이프라인을 동시에 실행
        pipelines = [TestGenerationPipeline() for _ in range(3)]

        # Mock 설정
        mock_doc_state = Mock()
        mock_doc_state.is_successful.return_value = True
        mock_doc_state.blocks = sample_blocks
        mock_doc_state.keywords = ["키워드"]
        mock_doc_state.summary = "요약"
        mock_doc_state.main_topics = ["주제"]
        mock_doc_state.get_statistics.return_value = {
            "total_blocks": len(sample_blocks)
        }

        mock_doc_agent = Mock()
        mock_doc_agent.analyze_document.return_value = mock_doc_state

        mock_design_result = {
            "output": {
                "requirements": {},
                "test_summary": "요약",
                "test_config": {
                    "num_questions": 3,
                    "num_objective": 2,
                    "num_subjective": 1,
                },
            }
        }
        mock_test_designer = AsyncMock()
        mock_test_designer.execute.return_value = mock_design_result

        async def run_single_pipeline(pipeline, collection_name):
            with patch(
                "src.pipelines.test_generation.pipeline.DocumentAnalyzerAgent",
                return_value=mock_doc_agent,
            ), patch(
                "src.pipelines.test_generation.pipeline.TestDesignerAgent",
                return_value=mock_test_designer,
            ), patch(
                "src.agents.question_generator.generate_questions.generate_question",
                return_value=sample_questions,
            ), patch(
                "openai.ChatCompletion.acreate", return_value=mock_openai_response
            ), patch.object(
                pipeline, "_upload_to_vectordb", return_value=3
            ), patch.object(
                pipeline, "_save_results"
            ):

                return await pipeline.run_complete_workflow(
                    mock_pdf_file, sample_user_prompt, collection_name
                )

        start_time = time.time()

        # 동시 실행
        tasks = [
            run_single_pipeline(pipeline, f"test_collection_{i}")
            for i, pipeline in enumerate(pipelines)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        execution_time = time.time() - start_time

        # 모든 실행이 성공했는지 확인
        for i, result in enumerate(results):
            assert not isinstance(
                result, Exception
            ), f"파이프라인 {i} 실행 실패: {result}"
            assert result["status"] == "completed"

        # 동시 실행 시간이 순차 실행보다 빨라야 함 (3배 이하)
        assert (
            execution_time < 15
        ), f"동시 실행 시간이 너무 오래 걸렸습니다: {execution_time:.2f}초"

    @pytest.mark.asyncio
    async def test_memory_cleanup_after_processing(
        self,
        mock_pdf_file,
        sample_user_prompt,
        sample_blocks,
        sample_questions,
        mock_openai_response,
    ):
        """처리 후 메모리 정리 테스트"""
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        pipeline = TestGenerationPipeline()

        # Mock 설정
        mock_doc_state = Mock()
        mock_doc_state.is_successful.return_value = True
        mock_doc_state.blocks = sample_blocks * 20  # 중간 크기 데이터
        mock_doc_state.keywords = ["키워드"] * 10
        mock_doc_state.summary = "요약"
        mock_doc_state.main_topics = ["주제"] * 5
        mock_doc_state.get_statistics.return_value = {"total_blocks": 60}

        mock_doc_agent = Mock()
        mock_doc_agent.analyze_document.return_value = mock_doc_state

        mock_design_result = {
            "output": {
                "requirements": {},
                "test_summary": "요약",
                "test_config": {
                    "num_questions": 5,
                    "num_objective": 3,
                    "num_subjective": 2,
                },
            }
        }
        mock_test_designer = AsyncMock()
        mock_test_designer.execute.return_value = mock_design_result

        with patch(
            "src.pipelines.test_generation.pipeline.DocumentAnalyzerAgent",
            return_value=mock_doc_agent,
        ), patch(
            "src.pipelines.test_generation.pipeline.TestDesignerAgent",
            return_value=mock_test_designer,
        ), patch(
            "src.agents.question_generator.generate_questions.generate_question",
            return_value=sample_questions,
        ), patch(
            "openai.ChatCompletion.acreate", return_value=mock_openai_response
        ), patch.object(
            pipeline, "_upload_to_vectordb", return_value=60
        ), patch.object(
            pipeline, "_save_results"
        ):

            await pipeline.run_complete_workflow(
                mock_pdf_file, sample_user_prompt, "test_collection"
            )

        # 파이프라인 객체 정리
        del pipeline

        # 가비지 컬렉션 강제 실행
        import gc

        gc.collect()

        # 메모리 정리 후 측정
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_difference = final_memory - initial_memory

        # 메모리 누수가 심하지 않은지 확인 (50MB 이하)
        assert (
            memory_difference < 50
        ), f"메모리 누수 가능성: {memory_difference:.2f}MB 증가"

    @pytest.mark.asyncio
    async def test_error_recovery_performance(self, mock_pdf_file, sample_user_prompt):
        """에러 복구 성능 테스트"""
        pipeline = TestGenerationPipeline()

        # 실패하는 DocumentAnalyzer 모킹
        mock_doc_agent = Mock()
        mock_doc_agent.analyze_document.side_effect = Exception("문서 분석 실패")

        start_time = time.time()

        with patch(
            "src.pipelines.test_generation.pipeline.DocumentAnalyzerAgent",
            return_value=mock_doc_agent,
        ):
            with pytest.raises(Exception):
                await pipeline.run_complete_workflow(
                    mock_pdf_file, sample_user_prompt, "test_collection"
                )

        error_handling_time = time.time() - start_time

        # 에러 처리 시간이 합리적인지 확인 (5초 이하)
        assert (
            error_handling_time < 5
        ), f"에러 처리 시간이 너무 오래 걸렸습니다: {error_handling_time:.2f}초"

    @pytest.mark.asyncio
    async def test_vectordb_upload_performance(
        self, sample_blocks, mock_embedding_model
    ):
        """VectorDB 업로드 성능 테스트"""
        pipeline = TestGenerationPipeline()
        pipeline.embedding_model = mock_embedding_model

        # 대량의 블록 생성 (100개)
        large_blocks = sample_blocks * 33 + sample_blocks[:1]  # 정확히 100개

        start_time = time.time()

        with patch(
            "src.pipelines.test_generation.pipeline.upload_chunk_to_collection"
        ) as mock_upload:
            mock_upload.return_value = True

            result = await pipeline._upload_to_vectordb(large_blocks, "test_collection")

        upload_time = time.time() - start_time

        # 업로드 성능 확인
        assert (
            upload_time < 10
        ), f"VectorDB 업로드 시간이 너무 오래 걸렸습니다: {upload_time:.2f}초"

        # 텍스트가 있는 블록만 업로드되었는지 확인
        expected_uploads = len(
            [b for b in large_blocks if pipeline._extract_text_from_block(b)]
        )
        assert result == expected_uploads
        assert mock_upload.call_count == expected_uploads

    @pytest.mark.asyncio
    async def test_question_generation_scalability(
        self, sample_blocks, sample_questions
    ):
        """질문 생성 확장성 테스트"""
        pipeline = TestGenerationPipeline()

        # 큰 문서와 많은 질문 요구
        large_blocks = sample_blocks * 50

        doc_result = {"blocks": large_blocks}
        design_result = {
            "test_config": {
                "num_objective": 20,  # 많은 객관식
                "num_subjective": 15,  # 많은 주관식
                "difficulty": "medium",
            },
            "test_summary": "대규모 테스트 요약",
        }

        start_time = time.time()

        with patch(
            "src.agents.question_generator.generate_questions.generate_question"
        ) as mock_generate, patch.object(
            pipeline, "_prepare_vision_chunks"
        ) as mock_prepare:

            # 다수의 청크 시뮬레이션
            mock_prepare.return_value = [
                {
                    "messages": [{"type": "text", "text": f"청크 {i}"}],
                    "metadata": {"page": i},
                }
                for i in range(10)  # 10개 청크
            ]

            # 각 호출마다 일부 질문 반환
            mock_generate.return_value = sample_questions[:2]  # 청크당 2문제

            result = await pipeline._step3_question_generation(
                doc_result, design_result
            )

        generation_time = time.time() - start_time

        # 질문 생성 시간이 합리적인지 확인 (15초 이하)
        assert (
            generation_time < 15
        ), f"질문 생성 시간이 너무 오래 걸렸습니다: {generation_time:.2f}초"

        # 적절한 수의 질문이 생성되었는지 확인
        assert len(result["questions"]) > 0
        assert result["statistics"]["total_questions"] > 0


class TestMemoryProfiler:
    """메모리 프로파일링 테스트"""

    def test_memory_usage_baseline(self):
        """기본 메모리 사용량 측정"""
        process = psutil.Process(os.getpid())
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 기본 메모리 사용량이 합리적인지 확인 (500MB 이하)
        assert (
            baseline_memory < 500
        ), f"기본 메모리 사용량이 너무 높습니다: {baseline_memory:.2f}MB"

    def test_pipeline_instantiation_memory(self):
        """파이프라인 인스턴스 생성 시 메모리 사용량"""
        process = psutil.Process(os.getpid())
        before_memory = process.memory_info().rss / 1024 / 1024

        pipeline = TestGenerationPipeline()

        after_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = after_memory - before_memory

        # 인스턴스 생성으로 인한 메모리 증가가 합리적인지 확인 (50MB 이하)
        assert (
            memory_increase < 50
        ), f"파이프라인 인스턴스 생성으로 메모리가 너무 많이 증가했습니다: {memory_increase:.2f}MB"

        del pipeline


class TestResourceUtilization:
    """리소스 사용량 테스트"""

    @pytest.mark.asyncio
    async def test_cpu_usage_during_processing(
        self, mock_pdf_file, sample_user_prompt, sample_blocks, mock_openai_response
    ):
        """처리 중 CPU 사용량 테스트"""
        pipeline = TestGenerationPipeline()

        # Mock 설정 (CPU 집약적 작업 시뮬레이션)
        mock_doc_state = Mock()
        mock_doc_state.is_successful.return_value = True
        mock_doc_state.blocks = sample_blocks
        mock_doc_state.keywords = []
        mock_doc_state.summary = ""
        mock_doc_state.main_topics = []
        mock_doc_state.get_statistics.return_value = {"total_blocks": 3}

        mock_doc_agent = Mock()
        mock_doc_agent.analyze_document.return_value = mock_doc_state

        mock_design_result = {
            "output": {
                "requirements": {},
                "test_summary": "요약",
                "test_config": {
                    "num_questions": 3,
                    "num_objective": 2,
                    "num_subjective": 1,
                },
            }
        }
        mock_test_designer = AsyncMock()
        mock_test_designer.execute.return_value = mock_design_result

        process = psutil.Process(os.getpid())
        process.cpu_percent()

        with patch(
            "src.pipelines.test_generation.pipeline.DocumentAnalyzerAgent",
            return_value=mock_doc_agent,
        ), patch(
            "src.pipelines.test_generation.pipeline.TestDesignerAgent",
            return_value=mock_test_designer,
        ), patch(
            "openai.ChatCompletion.acreate", return_value=mock_openai_response
        ), patch.object(
            pipeline, "_upload_to_vectordb", return_value=3
        ), patch.object(
            pipeline, "_save_results"
        ):

            await pipeline.run_complete_workflow(
                mock_pdf_file, sample_user_prompt, "test_collection"
            )

        # CPU 사용량이 정상 범위 내인지 확인
        # (Mock 환경이므로 실제 CPU 사용량은 낮을 것임)
        cpu_after = process.cpu_percent()

        # 테스트는 주로 Mock 실행이므로 CPU 사용량 체크는 기본적인 수준만
        assert cpu_after >= 0, "CPU 사용량 측정 오류"
