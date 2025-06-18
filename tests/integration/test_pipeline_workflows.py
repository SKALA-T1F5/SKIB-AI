"""
테스트 생성 파이프라인 통합 테스트
"""

import pytest
import os
import json
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from src.pipelines.test_generation.pipeline import TestGenerationPipeline, generate_test_from_document


class TestTestGenerationPipeline:
    """TestGenerationPipeline 통합 테스트 클래스"""
    
    @pytest.mark.asyncio
    async def test_pipeline_initialization(self):
        """파이프라인 초기화 테스트"""
        pipeline = TestGenerationPipeline()
        
        assert pipeline.embedding_model is not None
        assert pipeline.document_analyzer is None
        assert pipeline.test_designer is None
        
        await pipeline.initialize()
        
        assert pipeline.document_analyzer is not None
        assert pipeline.test_designer is not None
    
    @pytest.mark.asyncio
    @patch('src.pipelines.test_generation.pipeline.upload_chunk_to_collection')
    @patch('src.agents.question_generator.tools.question_generator.QuestionGenerator._generate_question')
    async def test_run_complete_workflow_success(
        self,
        mock_generate_question,
        mock_upload_chunk,
        mock_pdf_file,
        sample_user_prompt,
        sample_blocks,
        sample_questions,
        mock_openai_response,
        temp_output_dir
    ):
        """전체 워크플로우 성공 테스트"""
        pipeline = TestGenerationPipeline()
        
        # Mock 설정
        mock_generate_question.return_value = sample_questions
        mock_upload_chunk.return_value = True
        
        # DocumentAnalyzerAgent 모킹
        mock_doc_state = Mock()
        mock_doc_state.is_successful.return_value = True
        mock_doc_state.blocks = sample_blocks
        mock_doc_state.total_blocks = len(sample_blocks)
        mock_doc_state.text_blocks = 2
        mock_doc_state.table_blocks = 1
        mock_doc_state.image_blocks = 0
        mock_doc_state.keywords = ["프로세스", "업무"]
        mock_doc_state.summary = "테스트 문서 요약"
        mock_doc_state.main_topics = ["프로세스 관리"]
        mock_doc_state.get_statistics.return_value = {
            "total_blocks": len(sample_blocks),
            "block_breakdown": {"text": 2, "table": 1, "image": 0}
        }
        
        mock_doc_agent = Mock()
        mock_doc_agent.analyze_document.return_value = mock_doc_state
        
        # TestDesignerAgent 모킹
        mock_design_result = {
            "output": {
                "requirements": {"user_prompt": sample_user_prompt},
                "test_summary": "테스트 요약입니다",
                "test_config": {
                    "num_questions": 5,
                    "num_objective": 3,
                    "num_subjective": 2,
                    "difficulty": "medium"
                }
            }
        }
        
        mock_test_designer = AsyncMock()
        mock_test_designer.execute.return_value = mock_design_result
        
        # 출력 디렉토리 모킹
        with patch('src.pipelines.test_generation.pipeline.DocumentAnalyzerAgent', return_value=mock_doc_agent), \
             patch('src.pipelines.test_generation.pipeline.TestDesignerAgent', return_value=mock_test_designer), \
             patch('openai.ChatCompletion.acreate', return_value=mock_openai_response), \
             patch('os.makedirs'), \
             patch('builtins.open', create=True) as mock_file:
            
            # 파이프라인 실행
            result = await pipeline.run_complete_workflow(
                pdf_path=mock_pdf_file,
                user_prompt=sample_user_prompt,
                collection_name="test_collection",
                difficulty="medium",
                upload_to_vectordb=True
            )
        
        # 검증
        assert result["status"] == "completed"
        assert "pipeline_info" in result
        assert "document_analysis" in result
        assert "test_design" in result
        assert "questions" in result
        
        # 파이프라인 정보 검증
        pipeline_info = result["pipeline_info"]
        assert pipeline_info["collection_name"] == "test_collection"
        assert pipeline_info["user_prompt"] == sample_user_prompt
        assert pipeline_info["difficulty"] == "medium"
        assert pipeline_info["processing_time"] > 0
        
        # 문서 분석 결과 검증
        doc_analysis = result["document_analysis"]
        assert doc_analysis["keywords"] == ["프로세스", "업무"]
        assert doc_analysis["summary"] == "테스트 문서 요약"
        assert doc_analysis["vectordb_uploaded"] is True
        
        # 테스트 설계 결과 검증
        test_design = result["test_design"]
        assert test_design["test_summary"] == "테스트 요약입니다"
        assert test_design["test_config"]["num_questions"] == 5
        
        # 질문 생성 결과 검증
        questions = result["questions"]
        assert len(questions["questions"]) == len(sample_questions)
        assert questions["statistics"]["total_questions"] == len(sample_questions)
    
    @pytest.mark.asyncio
    async def test_step1_document_analysis(
        self,
        mock_pdf_file,
        sample_blocks,
        mock_embedding_model
    ):
        """1단계 문서 분석 테스트"""
        pipeline = TestGenerationPipeline()
        pipeline.embedding_model = mock_embedding_model
        
        # DocumentAnalyzerAgent 모킹
        mock_doc_state = Mock()
        mock_doc_state.is_successful.return_value = True
        mock_doc_state.blocks = sample_blocks
        mock_doc_state.keywords = ["키워드1", "키워드2"]
        mock_doc_state.summary = "문서 요약"
        mock_doc_state.main_topics = ["주제1"]
        mock_doc_state.get_statistics.return_value = {"total_blocks": 3}
        
        mock_doc_agent = Mock()
        mock_doc_agent.analyze_document.return_value = mock_doc_state
        
        with patch('src.pipelines.test_generation.pipeline.DocumentAnalyzerAgent', return_value=mock_doc_agent), \
             patch.object(pipeline, '_upload_to_vectordb', return_value=3) as mock_upload:
            
            result = await pipeline._step1_document_analysis(
                mock_pdf_file, "test_collection", True
            )
        
        # 검증
        assert result["blocks"] == sample_blocks
        assert result["keywords"] == ["키워드1", "키워드2"]
        assert result["summary"] == "문서 요약"
        assert result["main_topics"] == ["주제1"]
        assert result["vectordb_uploaded"] is True
        
        mock_upload.assert_called_once_with(sample_blocks, "test_collection")
    
    @pytest.mark.asyncio
    async def test_step2_test_design(
        self,
        sample_keywords,
        sample_document_summary,
        sample_document_topics,
        sample_user_prompt
    ):
        """2단계 테스트 설계 테스트"""
        pipeline = TestGenerationPipeline()
        
        doc_result = {
            "keywords": sample_keywords,
            "summary": sample_document_summary,
            "main_topics": sample_document_topics
        }
        
        # TestDesignerAgent 모킹
        mock_design_result = {
            "output": {
                "requirements": {"user_prompt": sample_user_prompt},
                "test_summary": "생성된 테스트 요약",
                "test_config": {
                    "num_questions": 7,
                    "num_objective": 4,
                    "num_subjective": 3,
                    "difficulty": "hard"
                }
            }
        }
        
        mock_test_designer = AsyncMock()
        mock_test_designer.execute.return_value = mock_design_result
        pipeline.test_designer = mock_test_designer
        
        result = await pipeline._step2_test_design(
            doc_result, sample_user_prompt, "hard"
        )
        
        # 검증
        assert result == mock_design_result["output"]
        
        # execute 호출 인자 확인
        call_args = mock_test_designer.execute.call_args[0][0]
        assert call_args["user_prompt"] == sample_user_prompt
        assert call_args["keywords"] == sample_keywords
        assert call_args["document_summary"] == sample_document_summary
        assert call_args["difficulty"] == "hard"
    
    @pytest.mark.asyncio
    @patch('src.agents.question_generator.generate_questions.generate_question')
    async def test_step3_question_generation(
        self,
        mock_generate_question,
        sample_blocks,
        sample_questions
    ):
        """3단계 질문 생성 테스트"""
        pipeline = TestGenerationPipeline()
        
        mock_generate_question.return_value = sample_questions
        
        doc_result = {"blocks": sample_blocks}
        design_result = {
            "test_config": {
                "num_objective": 3,
                "num_subjective": 2,
                "difficulty": "medium"
            },
            "test_summary": "테스트 요약"
        }
        
        with patch.object(pipeline, '_prepare_vision_chunks') as mock_prepare:
            # Vision 청크 모킹
            mock_prepare.return_value = [
                {
                    "messages": [{"type": "text", "text": "테스트 내용"}],
                    "metadata": {"page": 1}
                }
            ]
            
            result = await pipeline._step3_question_generation(doc_result, design_result)
        
        # 검증
        assert len(result["questions"]) == len(sample_questions)
        assert result["statistics"]["total_questions"] == len(sample_questions)
        assert result["statistics"]["target_objective"] == 3
        assert result["statistics"]["target_subjective"] == 2
        
        mock_generate_question.assert_called()
    
    def test_extract_text_from_block_paragraph(self):
        """단락 블록에서 텍스트 추출 테스트"""
        pipeline = TestGenerationPipeline()
        
        block = {
            "type": "paragraph",
            "content": "이것은 테스트 문단입니다."
        }
        
        result = pipeline._extract_text_from_block(block)
        assert result == "이것은 테스트 문단입니다."
    
    def test_extract_text_from_block_table(self):
        """표 블록에서 텍스트 추출 테스트"""
        pipeline = TestGenerationPipeline()
        
        block = {
            "type": "table",
            "content": {
                "headers": ["이름", "나이"],
                "data": [["홍길동", "30"], ["김철수", "25"]]
            }
        }
        
        result = pipeline._extract_text_from_block(block)
        assert "이름 나이" in result
        assert "홍길동 30" in result
        assert "김철수 25" in result
    
    def test_extract_text_from_block_empty(self):
        """빈 블록에서 텍스트 추출 테스트"""
        pipeline = TestGenerationPipeline()
        
        block = {"type": "unknown", "content": ""}
        result = pipeline._extract_text_from_block(block)
        assert result == ""
    
    def test_table_to_text(self):
        """표를 텍스트로 변환 테스트"""
        pipeline = TestGenerationPipeline()
        
        table_data = {
            "headers": ["열1", "열2"],
            "data": [["값1", "값2"], ["값3", "값4"]]
        }
        
        result = pipeline._table_to_text(table_data)
        expected = "열1 열2 값1 값2 값3 값4"
        assert result == expected
    
    def test_table_to_text_no_headers(self):
        """헤더 없는 표 변환 테스트"""
        pipeline = TestGenerationPipeline()
        
        table_data = {"data": [["값1", "값2"]]}
        result = pipeline._table_to_text(table_data)
        assert result == "값1 값2"
    
    def test_table_to_text_invalid(self):
        """잘못된 표 데이터 처리 테스트"""
        pipeline = TestGenerationPipeline()
        
        result = pipeline._table_to_text("잘못된 데이터")
        assert result == ""
        
        result = pipeline._table_to_text({"no_data": "field"})
        assert result == ""
    
    @pytest.mark.asyncio
    @patch('src.pipelines.test_generation.pipeline.upload_chunk_to_collection')
    async def test_upload_to_vectordb(
        self,
        mock_upload_chunk,
        sample_blocks,
        mock_embedding_model
    ):
        """VectorDB 업로드 테스트"""
        pipeline = TestGenerationPipeline()
        pipeline.embedding_model = mock_embedding_model
        
        mock_upload_chunk.return_value = True
        
        result = await pipeline._upload_to_vectordb(sample_blocks, "test_collection")
        
        # 텍스트가 있는 블록만 업로드되어야 함 (heading + paragraph = 2개)
        assert result == 2
        assert mock_upload_chunk.call_count == 2
    
    @pytest.mark.asyncio
    async def test_save_results(self, sample_test_result, temp_output_dir):
        """결과 저장 테스트"""
        pipeline = TestGenerationPipeline()
        
        with patch('os.makedirs') as mock_makedirs, \
             patch('builtins.open', create=True) as mock_open, \
             patch('json.dump') as mock_json_dump:
            
            await pipeline._save_results(sample_test_result, "test_collection")
        
        # 디렉토리 생성 확인
        mock_makedirs.assert_called_once_with("data/outputs", exist_ok=True)
        
        # 파일 생성 확인 (전체 결과 + 문제만)
        assert mock_open.call_count == 2
        assert mock_json_dump.call_count == 2


class TestPipelineErrorHandling:
    """파이프라인 에러 처리 테스트"""
    
    @pytest.mark.asyncio
    async def test_document_analysis_failure(self, mock_pdf_file, sample_user_prompt):
        """문서 분석 실패 처리 테스트"""
        pipeline = TestGenerationPipeline()
        
        # DocumentAnalyzerAgent가 실패하도록 모킹
        mock_doc_state = Mock()
        mock_doc_state.is_successful.return_value = False
        mock_doc_state.error_message = "파일 읽기 실패"
        
        mock_doc_agent = Mock()
        mock_doc_agent.analyze_document.return_value = mock_doc_state
        
        with patch('src.pipelines.test_generation.pipeline.DocumentAnalyzerAgent', return_value=mock_doc_agent):
            with pytest.raises(Exception) as exc_info:
                await pipeline.run_complete_workflow(
                    mock_pdf_file, sample_user_prompt, "test_collection"
                )
            
            assert "문서 분석 실패" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_test_design_failure(
        self,
        mock_pdf_file,
        sample_user_prompt,
        sample_blocks
    ):
        """테스트 설계 실패 처리 테스트"""
        pipeline = TestGenerationPipeline()
        
        # 문서 분석은 성공
        mock_doc_state = Mock()
        mock_doc_state.is_successful.return_value = True
        mock_doc_state.blocks = sample_blocks
        mock_doc_state.keywords = []
        mock_doc_state.summary = ""
        mock_doc_state.main_topics = []
        mock_doc_state.get_statistics.return_value = {"total_blocks": 1}
        
        mock_doc_agent = Mock()
        mock_doc_agent.analyze_document.return_value = mock_doc_state
        
        # 테스트 설계는 실패
        mock_test_designer = AsyncMock()
        mock_test_designer.execute.return_value = {}  # 빈 결과
        
        with patch('src.pipelines.test_generation.pipeline.DocumentAnalyzerAgent', return_value=mock_doc_agent), \
             patch('src.pipelines.test_generation.pipeline.TestDesignerAgent', return_value=mock_test_designer):
            
            with pytest.raises(Exception) as exc_info:
                await pipeline.run_complete_workflow(
                    mock_pdf_file, sample_user_prompt, "test_collection"
                )
            
            assert "테스트 설계 실패" in str(exc_info.value)
    
    @pytest.mark.asyncio
    @patch('src.pipelines.test_generation.pipeline.upload_chunk_to_collection')
    async def test_vectordb_upload_partial_failure(
        self,
        mock_upload_chunk,
        sample_blocks,
        mock_embedding_model
    ):
        """VectorDB 업로드 부분 실패 테스트"""
        pipeline = TestGenerationPipeline()
        pipeline.embedding_model = mock_embedding_model
        
        # 첫 번째 업로드는 성공, 두 번째는 실패
        mock_upload_chunk.side_effect = [True, Exception("업로드 실패")]
        
        result = await pipeline._upload_to_vectordb(sample_blocks, "test_collection")
        
        # 성공한 것만 카운트되어야 함
        assert result == 1


class TestConvenienceFunctions:
    """편의 함수 테스트"""
    
    @pytest.mark.asyncio
    @patch('src.pipelines.test_generation.pipeline.TestGenerationPipeline')
    async def test_generate_test_from_document(
        self,
        mock_pipeline_class,
        sample_pdf_path,
        sample_user_prompt,
        sample_test_result
    ):
        """문서로부터 테스트 생성 편의 함수 테스트"""
        # Mock 설정
        mock_pipeline = AsyncMock()
        mock_pipeline.run_complete_workflow.return_value = sample_test_result
        mock_pipeline_class.return_value = mock_pipeline
        
        # 함수 호출
        result = await generate_test_from_document(
            pdf_path=sample_pdf_path,
            user_prompt=sample_user_prompt,
            collection_name="test_collection",
            difficulty="hard",
            upload_to_vectordb=False
        )
        
        # 검증
        mock_pipeline_class.assert_called_once()
        mock_pipeline.run_complete_workflow.assert_called_once_with(
            sample_pdf_path, sample_user_prompt, "test_collection", "hard", False
        )
        assert result == sample_test_result


class TestPipelinePerformance:
    """파이프라인 성능 테스트"""
    
    @pytest.mark.asyncio
    async def test_processing_time_tracking(
        self,
        mock_pdf_file,
        sample_user_prompt,
        sample_blocks,
        sample_questions,
        mock_openai_response
    ):
        """처리 시간 추적 테스트"""
        pipeline = TestGenerationPipeline()
        
        # 모든 단계 모킹 (빠른 실행)
        mock_doc_state = Mock()
        mock_doc_state.is_successful.return_value = True
        mock_doc_state.blocks = sample_blocks
        mock_doc_state.keywords = []
        mock_doc_state.summary = ""
        mock_doc_state.main_topics = []
        mock_doc_state.get_statistics.return_value = {"total_blocks": 1}
        
        mock_doc_agent = Mock()
        mock_doc_agent.analyze_document.return_value = mock_doc_state
        
        mock_design_result = {
            "output": {
                "requirements": {},
                "test_summary": "요약",
                "test_config": {"num_questions": 2, "num_objective": 1, "num_subjective": 1}
            }
        }
        mock_test_designer = AsyncMock()
        mock_test_designer.execute.return_value = mock_design_result
        
        with patch('src.pipelines.test_generation.pipeline.DocumentAnalyzerAgent', return_value=mock_doc_agent), \
             patch('src.pipelines.test_generation.pipeline.TestDesignerAgent', return_value=mock_test_designer), \
             patch('src.agents.question_generator.tools.question_generator.QuestionGenerator._generate_question', return_value=sample_questions), \
             patch('openai.ChatCompletion.acreate', return_value=mock_openai_response), \
             patch.object(pipeline, '_upload_to_vectordb', return_value=1), \
             patch.object(pipeline, '_save_results'):
            
            result = await pipeline.run_complete_workflow(
                mock_pdf_file, sample_user_prompt, "test_collection"
            )
        
        # 처리 시간이 기록되었는지 확인
        processing_time = result["pipeline_info"]["processing_time"]
        assert isinstance(processing_time, (int, float))
        assert processing_time >= 0