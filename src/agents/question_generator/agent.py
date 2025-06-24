"""
문제 생성 Agent
- GPT-4 Vision을 사용한 자동 문제 생성
- 테스트 요약 및 설정 파일 생성
- 문제 결과 저장 및 관리
"""

import json
import os
import glob
from datetime import datetime
from typing import Dict, List, Any

from .tools.question_generator import QuestionGenerator
from .tools.test_plan_handler import TestPlanHandler
from .tools.vector_search import VectorSearchHandler
from .tools.result_saver import ResultSaver


class QuestionGeneratorAgent:
    """문제 생성 전문 Agent"""

    def __init__(self, collection_name: str = None):
        self.collection_name = collection_name
        # 이미지 저장 디렉토리 설정
        if collection_name:
            from utils.naming import filename_to_collection

            normalized_name = filename_to_collection(collection_name)
            self.image_save_dir = f"data/images/{normalized_name}"
        else:
            self.image_save_dir = "data/images/unified"
        self.question_generator = QuestionGenerator(self.image_save_dir)
        
        # Tools 초기화
        self.test_plan_handler = TestPlanHandler()
        self.vector_search_handler = VectorSearchHandler()
        self.result_saver = ResultSaver()






    def generate_enhanced_questions_from_test_plans(
        self,
        total_test_plan_path: str = None,
        document_test_plan_path: str = None,
        total_test_plan_data: Dict = None,
        document_test_plan_data: Dict = None,
        collection_name: str = None
    ) -> Dict[str, Any]:
        """
        테스트 계획을 기반으로 향상된 문제 생성
        
        Args:
            total_test_plan_path: 전체 테스트 계획 파일 경로 (선택사항)
            document_test_plan_path: 문서별 테스트 계획 파일 경로 (선택사항)
            total_test_plan_data: 전체 테스트 계획 데이터 딕셔너리 (선택사항)
            document_test_plan_data: 문서별 테스트 계획 데이터 딕셔너리 (선택사항)
            collection_name: VectorDB 컶렉션명
        
        Returns:
            Dict: 문제 생성 결과
        """
        print("🚀 향상된 문제 생성기 시작")
        
        # 1. Test Plan 로드 (우선순위: 데이터 > 경로 > 자동 검색)
        total_plan = None
        document_plan = None
        
        if total_test_plan_data and document_test_plan_data:
            # 직접 딕셔너리 데이터 사용
            total_plan = total_test_plan_data
            document_plan = document_test_plan_data
            print("📋 Test Plan 데이터를 직접 딕셔너리로 받음")
        elif total_test_plan_path and document_test_plan_path:
            # 지정된 경로에서 로드
            total_plan, document_plan = self.test_plan_handler.load_specific_test_plans(
                total_test_plan_path, document_test_plan_path
            )
            if not total_plan or not document_plan:
                return {"status": "failed", "error": "지정된 Test plan 파일 로드 실패"}
        else:
            # 자동으로 최신 파일 찾기
            total_plan, document_plan = self.test_plan_handler.load_latest_test_plans()
            if not total_plan or not document_plan:
                return {"status": "failed", "error": "Test plan 파일을 찾을 수 없습니다."}
        
        all_generated_questions = []
        generation_summary = {
            'total_documents': len(document_plan.get('document_plans', [])),
            'documents_processed': [],
            'total_questions_generated': 0,
            'basic_questions': 0,
            'extra_questions': 0
        }
        
        # 2. 각 문서별로 문제 생성
        for doc_plan in document_plan.get('document_plans', []):
            document_name = doc_plan.get('document_name', 'Unknown')
            keywords = doc_plan.get('keywords', [])
            recommended = doc_plan.get('recommended_questions', {})
            
            print(f"\n📄 문서 처리: {document_name}")
            print(f"🔑 키워드: {', '.join(keywords)}")
            print(f"📊 추천 문제수: 객관식 {recommended.get('objective', 0)}개, 주관식 {recommended.get('subjective', 0)}개")
            
            # VectorDB에서 키워드 관련 콘텐츠 검색 (문서명을 자동으로 collection명으로 변환)
            if document_name:
                related_content = self.vector_search_handler.search_keywords_in_collection(keywords, document_name)
            else:
                # 문서명이 없는 경우 fallback 컬렉션들에서 검색
                related_content = self.vector_search_handler.search_with_fallback_collections(
                    keywords=keywords,
                    primary_document_name=None
                )
            
            doc_questions = []
            
            # 3. 기본 문제 생성 (추천 문제수)
            basic_questions = self._generate_questions_with_context(
                keywords=keywords,
                related_content=related_content,
                document_name=document_name,
                num_objective=recommended.get('objective', 0),
                num_subjective=recommended.get('subjective', 0),
                question_type='basic'
            )
            doc_questions.extend(basic_questions)
            
            # 4. 여분 문제 생성 (키워드별 2문제씩)
            extra_objective, extra_subjective = self.test_plan_handler.calculate_extra_questions(keywords)
            
            if extra_objective > 0 or extra_subjective > 0:
                print(f"  🎯 여분 문제 생성: 객관식 {extra_objective}개, 주관식 {extra_subjective}개")
                
                extra_questions = self._generate_questions_with_context(
                    keywords=keywords,
                    related_content=related_content,
                    document_name=document_name,
                    num_objective=extra_objective,
                    num_subjective=extra_subjective,
                    question_type='advanced'
                )
                doc_questions.extend(extra_questions)
            
            # 결과 요약
            basic_count = len(basic_questions)
            extra_count = len(doc_questions) - basic_count
            
            generation_summary['documents_processed'].append({
                'document_name': document_name,
                'keywords': keywords,
                'basic_questions': basic_count,
                'extra_questions': extra_count,
                'total_questions': len(doc_questions)
            })
            
            generation_summary['basic_questions'] += basic_count
            generation_summary['extra_questions'] += extra_count
            
            all_generated_questions.extend(doc_questions)
            
            print(f"  ✅ '{document_name}' 문제 생성 완료: 기본 {basic_count}개 + 여분 {extra_count}개 = 총 {len(doc_questions)}개")
        
        generation_summary['total_questions_generated'] = len(all_generated_questions)
        
        # 5. 결과 저장
        result = self.result_saver.save_enhanced_questions(
            questions=all_generated_questions,
            summary=generation_summary,
            total_plan=total_plan,
            document_plan=document_plan
        )
        
        return result

    def _generate_questions_with_context(
        self, 
        keywords: List[str], 
        related_content: List[Dict],
        document_name: str,
        num_objective: int,
        num_subjective: int,
        question_type: str = "basic"
    ) -> List[Dict]:
        """콘텍스트를 활용한 문제 생성 (기존 QuestionGenerator 활용)"""
        if num_objective == 0 and num_subjective == 0:
            return []
        
        try:
            # 관련 콘텐츠를 블록 형태로 변환
            context_blocks = self._convert_content_to_blocks(related_content, keywords)
            
            if not context_blocks:
                print(f"  ⚠️ 콘텍스트 블록을 생성할 수 없습니다.")
                return []
            
            # 기존 QuestionGenerator 활용
            context_blocks = self.question_generator.generate_questions_for_blocks(
                blocks=context_blocks,
                num_objective=num_objective,
                num_subjective=num_subjective
            )
            
            # 생성된 문제 추출 및 메타데이터 추가
            questions = []
            for block in context_blocks:
                if "questions" in block:
                    for question in block["questions"]:
                        # 메타데이터 추가
                        question['generation_type'] = question_type
                        question['document_source'] = document_name
                        question['generated_at'] = datetime.now().isoformat()
                        question['source_keywords'] = keywords
                        questions.append(question)
            
            print(f"  ✅ {len(questions)}개 {question_type} 문제 생성 완료")
            return questions
            
        except Exception as e:
            print(f"  ❌ {question_type} 문제 생성 실패: {e}")
            return []

    def _convert_content_to_blocks(self, related_content: List[Dict], keywords: List[str]) -> List[Dict]:
        """관련 콘텐츠를 블록 형태로 변환"""
        return self.vector_search_handler.convert_content_to_blocks(related_content, keywords)



# 편의 함수
def generate_enhanced_questions_from_test_plans(
    total_test_plan_path: str = None,
    document_test_plan_path: str = None,
    total_test_plan_data: Dict = None,
    document_test_plan_data: Dict = None,
    collection_name: str = None
) -> Dict[str, Any]:
    """
    테스트 계획을 기반으로 향상된 문제 생성 편의 함수
    
    Args:
        total_test_plan_path: 전체 테스트 계획 파일 경로 (선택사항)
        document_test_plan_path: 문서별 테스트 계획 파일 경로 (선택사항)  
        total_test_plan_data: 전체 테스트 계획 데이터 딕셔너리 (선택사항)
        document_test_plan_data: 문서별 테스트 계획 데이터 딕셔너리 (선택사항)
        collection_name: VectorDB 컬렉션명
    
    Returns:
        Dict: 향상된 문제 생성 결과
    """
    agent = QuestionGeneratorAgent()
    return agent.generate_enhanced_questions_from_test_plans(
        total_test_plan_path=total_test_plan_path,
        document_test_plan_path=document_test_plan_path,
        total_test_plan_data=total_test_plan_data,
        document_test_plan_data=document_test_plan_data,
        collection_name=collection_name
    )


