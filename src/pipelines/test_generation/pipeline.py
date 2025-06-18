"""
테스트 생성 Pipeline
전체 워크플로우를 관리하는 메인 파이프라인

워크플로우:
1. 문서 분석 Agent -> 파싱 -> VectorDB 업로드 + 키워드/요약 생성
2. 테스트 설계 Agent -> GPT-4로 테스트 요약 + config 생성
3. 질문 생성 Agent -> GPT-4o Vision으로 문제 생성
"""

import os
import json
import time
from typing import Dict, Any, List
from sentence_transformers import SentenceTransformer

from src.agents.document_analyzer.agent import DocumentAnalyzerAgent
from src.agents.test_designer.agent import TestDesignerAgent
from src.agents.question_generator.tools.question_generator import QuestionGenerator
from db.vectorDB.weaviate_utils import upload_chunk_to_collection
from utils.change_name import normalize_collection_name


class TestGenerationPipeline:
    """테스트 생성 전체 파이프라인"""
    
    def __init__(self):
        self.embedding_model = SentenceTransformer("BAAI/bge-base-en")
        self.document_analyzer = None
        self.test_designer = None
        
    async def initialize(self):
        """파이프라인 초기화"""
        self.document_analyzer = DocumentAnalyzerAgent()
        self.test_designer = TestDesignerAgent()
        await self.test_designer.initialize()
    
    async def run_complete_workflow(
        self,
        pdf_path: str,
        user_prompt: str,
        collection_name: str = None,
        difficulty: str = "medium",
        upload_to_vectordb: bool = True
    ) -> Dict[str, Any]:
        """
        전체 워크플로우 실행
        
        Args:
            pdf_path: PDF 파일 경로
            user_prompt: 사용자 요청 프롬프트
            collection_name: 컬렉션명
            difficulty: 난이도
            upload_to_vectordb: VectorDB 업로드 여부
            
        Returns:
            전체 처리 결과
        """
        if not self.document_analyzer or not self.test_designer:
            await self.initialize()
        
        start_time = time.time()
        
        try:
            # 컬렉션명 설정
            if not collection_name:
                filename = os.path.splitext(os.path.basename(pdf_path))[0]
                collection_name = normalize_collection_name(filename)
            
            print(f"🚀 테스트 생성 파이프라인 시작")
            print(f"📁 컬렉션: {collection_name}")
            print(f"📄 문서: {pdf_path}")
            print(f"💭 사용자 요청: {user_prompt}")
            print("=" * 80)
            
            # 1단계: 문서 분석
            print("\n1️⃣ 문서 분석 및 처리")
            doc_result = await self._step1_document_analysis(
                pdf_path, collection_name, upload_to_vectordb
            )
            
            # 2단계: 테스트 설계
            print("\n2️⃣ 테스트 설계")
            design_result = await self._step2_test_design(
                doc_result, user_prompt, difficulty
            )
            
            # 3단계: 문제 생성
            print("\n3️⃣ 문제 생성")
            questions_result = await self._step3_question_generation(
                doc_result, design_result
            )
            
            # 결과 종합
            total_time = time.time() - start_time
            
            final_result = {
                "pipeline_info": {
                    "collection_name": collection_name,
                    "pdf_path": pdf_path,
                    "user_prompt": user_prompt,
                    "difficulty": difficulty,
                    "processing_time": round(total_time, 2),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "document_analysis": doc_result,
                "test_design": design_result,
                "questions": questions_result,
                "status": "completed"
            }
            
            # 결과 저장
            await self._save_results(final_result, collection_name)
            
            print(f"\n🎉 테스트 생성 완료!")
            print(f"⏱️  총 처리 시간: {total_time:.2f}초")
            print(f"📊 생성된 문제 수: {len(questions_result.get('questions', []))}개")
            
            return final_result
            
        except Exception as e:
            print(f"❌ 파이프라인 실행 실패: {e}")
            raise
    
    async def _step1_document_analysis(
        self, 
        pdf_path: str, 
        collection_name: str, 
        upload_to_vectordb: bool
    ) -> Dict[str, Any]:
        """1단계: 문서 분석 및 VectorDB 업로드"""
        
        # 문서 분석 실행
        print("  📄 문서 구조 분석 중...")
        self.document_analyzer = DocumentAnalyzerAgent(collection_name)
        doc_state = self.document_analyzer.analyze_document(
            pdf_path, 
            extract_keywords=True
        )
        
        if doc_state.get("processing_status") != "completed":
            raise Exception(f"문서 분석 실패: {doc_state.get('error_message', '알 수 없는 오류')}")
        
        print(f"  ✅ 분석 완료: {doc_state.get('total_blocks', 0)}개 블록")
        
        # VectorDB 업로드
        if upload_to_vectordb:
            print("  📤 VectorDB 업로드 중...")
            uploaded_count = await self._upload_to_vectordb(doc_state.get("blocks", []), collection_name)
            print(f"  ✅ 업로드 완료: {uploaded_count}개 청크")
        
        return {
            "blocks": doc_state.get("blocks", []),
            "statistics": {
                "total_blocks": doc_state.get("total_blocks", 0),
                "block_breakdown": {
                    "text": doc_state.get("text_blocks", 0),
                    "table": doc_state.get("table_blocks", 0),
                    "image": doc_state.get("image_blocks", 0)
                }
            },
            "keywords": doc_state.get("keywords", []),
            "summary": doc_state.get("summary", ""),
            "main_topics": doc_state.get("main_topics", []),
            "vectordb_uploaded": upload_to_vectordb
        }
    
    async def _step2_test_design(
        self, 
        doc_result: Dict[str, Any], 
        user_prompt: str, 
        difficulty: str
    ) -> Dict[str, Any]:
        """2단계: 테스트 설계"""
        
        print("  🎯 테스트 요구사항 분석 중...")
        
        design_input = {
            "keywords": doc_result["keywords"],
            "document_summary": doc_result["summary"],
            "document_topics": doc_result["main_topics"],
            "user_prompt": user_prompt,
            "difficulty": difficulty,
            "test_type": "mixed",
            "time_limit": 60
        }
        
        design_state = await self.test_designer.execute(design_input)
        
        if design_state.get("status") != "completed":
            raise Exception("테스트 설계 실패")
        
        # BaseAgent의 execute 메소드에서 결과는 intermediate_results에 저장됨
        result = design_state.get("output") or design_state.get("intermediate_results", {})
        print(f"  ✅ 설계 완료: {result['test_config']['num_questions']}문제")
        
        return result
    
    async def _step3_question_generation(
        self, 
        doc_result: Dict[str, Any], 
        design_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """3단계: GPT-4o Vision으로 문제 생성"""
        
        print("  🤖 GPT-4o Vision 문제 생성 중...")
        
        test_config = design_result["test_config"]
        test_summary = design_result["test_summary"]
        
        # 블록들을 Vision 메시지로 변환
        vision_chunks = self._prepare_vision_chunks(doc_result["blocks"])
        
        all_questions = []
        target_objective = test_config["num_objective"]
        target_subjective = test_config["num_subjective"]
        
        generated_objective = 0
        generated_subjective = 0
        
        for i, chunk in enumerate(vision_chunks):
            if generated_objective >= target_objective and generated_subjective >= target_subjective:
                break
            
            print(f"    📝 청크 {i+1}/{len(vision_chunks)} 처리 중...")
            
            # 남은 문제 수 계산
            remaining_obj = max(0, target_objective - generated_objective)
            remaining_subj = max(0, target_subjective - generated_subjective)
            
            if remaining_obj == 0 and remaining_subj == 0:
                break
            
            # 청크별 분배
            chunk_obj = min(remaining_obj, max(1, remaining_obj // (len(vision_chunks) - i)))
            chunk_subj = min(remaining_subj, max(1, remaining_subj // (len(vision_chunks) - i)))
            
            if chunk_obj == 0 and chunk_subj == 0:
                continue
            
            try:
                # GPT-4o Vision으로 문제 생성
                generator = QuestionGenerator()
                questions = generator._generate_question(
                    messages=chunk["messages"],
                    source=os.path.basename(doc_result.get("pdf_path", "document")),
                    page=str(chunk["metadata"]["page"]),
                    num_objective=chunk_obj,
                    num_subjective=chunk_subj
                )
                
                if questions:
                    all_questions.extend(questions)
                    
                    # 생성된 문제 수 업데이트
                    for q in questions:
                        if q.get("type") == "OBJECTIVE":
                            generated_objective += 1
                        else:
                            generated_subjective += 1
                    
                    print(f"      ✅ {len(questions)}개 문제 생성")
                
            except Exception as e:
                print(f"      ⚠️ 청크 {i+1} 문제 생성 실패: {e}")
                continue
        
        print(f"  ✅ 총 {len(all_questions)}개 문제 생성 완료")
        print(f"    - 객관식: {generated_objective}개")
        print(f"    - 주관식: {generated_subjective}개")
        
        return {
            "questions": all_questions,
            "statistics": {
                "total_questions": len(all_questions),
                "objective_questions": generated_objective,
                "subjective_questions": generated_subjective,
                "target_objective": target_objective,
                "target_subjective": target_subjective
            },
            "test_config": test_config
        }
    
    def _prepare_vision_chunks(self, blocks: List[Dict]) -> List[Dict]:
        """블록들을 Vision API용 청크로 변환"""
        generator = QuestionGenerator()
        return generator._blocks_to_vision_chunks(blocks)
    
    async def _upload_to_vectordb(self, blocks: List[Dict], collection_name: str) -> int:
        """VectorDB에 블록들 업로드"""
        uploaded_count = 0
        
        for i, block in enumerate(blocks):
            try:
                # 텍스트 내용 추출
                content = self._extract_text_from_block(block)
                if not content:
                    continue
                
                # 청크 객체 생성
                chunk_obj = {
                    "chunk_id": f"{collection_name}_block_{i}",
                    "chunk_type": block.get("type", "unknown"),
                    "section_title": block.get("title", ""),
                    "source_text": content,
                    "project": collection_name,
                    "source": f"{collection_name}.pdf",
                    "page": str(block.get("metadata", {}).get("page", "N/A"))
                }
                
                # 벡터 임베딩 생성
                vector = self.embedding_model.encode(content).tolist()
                
                # 업로드
                upload_chunk_to_collection(chunk_obj, vector, collection_name)
                uploaded_count += 1
                
            except Exception as e:
                print(f"    ⚠️ 블록 {i} 업로드 실패: {e}")
                continue
        
        return uploaded_count
    
    def _extract_text_from_block(self, block: Dict) -> str:
        """블록에서 텍스트 추출"""
        block_type = block.get("type", "")
        content = block.get("content", "")
        
        if block_type in ["paragraph", "heading", "section"] and content:
            return str(content)
        elif block_type == "table" and isinstance(content, dict):
            # 표 내용을 텍스트로 변환
            return self._table_to_text(content)
        
        return ""
    
    def _table_to_text(self, table_data: Dict) -> str:
        """표 데이터를 텍스트로 변환"""
        if not isinstance(table_data, dict) or "data" not in table_data:
            return ""
        
        headers = table_data.get("headers", [])
        data = table_data.get("data", [])
        
        text_parts = []
        if headers:
            text_parts.append(" ".join(str(h) for h in headers))
        
        for row in data:
            text_parts.append(" ".join(str(cell) for cell in row))
        
        return " ".join(text_parts)
    
    async def _save_results(self, result: Dict[str, Any], collection_name: str):
        """결과 저장"""
        output_dir = "data/outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        # 전체 결과 저장
        result_path = os.path.join(output_dir, f"{collection_name}_test_generation_result.json")
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        # 문제만 별도 저장
        questions_path = os.path.join(output_dir, f"{collection_name}_questions.json")
        with open(questions_path, 'w', encoding='utf-8') as f:
            json.dump(result["questions"], f, ensure_ascii=False, indent=2)
        
        print(f"  💾 결과 저장: {result_path}")
        print(f"  💾 문제 저장: {questions_path}")


# 편의 함수
async def generate_test_from_document(
    pdf_path: str,
    user_prompt: str,
    collection_name: str = None,
    difficulty: str = "medium",
    upload_to_vectordb: bool = True
) -> Dict[str, Any]:
    """
    문서로부터 테스트 생성 편의 함수
    
    Args:
        pdf_path: PDF 파일 경로
        user_prompt: 사용자 요청
        collection_name: 컬렉션명
        difficulty: 난이도
        upload_to_vectordb: VectorDB 업로드 여부
        
    Returns:
        테스트 생성 결과
    """
    pipeline = TestGenerationPipeline()
    return await pipeline.run_complete_workflow(
        pdf_path, user_prompt, collection_name, difficulty, upload_to_vectordb
    )