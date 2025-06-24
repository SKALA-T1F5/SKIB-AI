"""
Test Plan 처리 관련 도구
"""

import json
import glob
import os
from typing import Dict, List, Tuple, Any


class TestPlanHandler:
    """Test Plan 파일 처리 클래스"""
    
    @staticmethod
    def load_latest_test_plans() -> Tuple[Dict, Dict]:
        """최신 테스트 계획 파일들 로드"""
        # 최신 파일 찾기
        total_files = glob.glob('data/outputs/total_test_plan/*.json')
        document_files = glob.glob('data/outputs/document_test_plan/*.json')
        
        if not total_files or not document_files:
            print("⚠️ Test plan 파일을 찾을 수 없습니다.")
            return {}, {}
        
        # 최신 파일 선택
        total_file = sorted(total_files)[-1]
        document_file = sorted(document_files)[-1]
        
        try:
            with open(total_file, 'r', encoding='utf-8') as f:
                total_plan = json.load(f)
            
            with open(document_file, 'r', encoding='utf-8') as f:
                document_plan = json.load(f)
            
            print(f"📋 로드된 Total Plan: {os.path.basename(total_file)}")
            print(f"📋 로드된 Document Plan: {os.path.basename(document_file)}")
            
            return total_plan, document_plan
        except Exception as e:
            print(f"⚠️ Test plan 파일 로드 실패: {e}")
            return {}, {}
    
    @staticmethod
    def load_specific_test_plans(total_path: str, document_path: str) -> Tuple[Dict, Dict]:
        """특정 테스트 계획 파일들 로드"""
        try:
            with open(total_path, 'r', encoding='utf-8') as f:
                total_plan = json.load(f)
            with open(document_path, 'r', encoding='utf-8') as f:
                document_plan = json.load(f)
            return total_plan, document_plan
        except Exception as e:
            print(f"⚠️ 지정된 Test plan 파일 로드 실패: {e}")
            return {}, {}
    
    @staticmethod
    def extract_document_info(document_plan: Dict) -> List[Dict[str, Any]]:
        """Document plan에서 문서 정보 추출"""
        documents_info = []
        
        for doc_plan in document_plan.get('document_plans', []):
            doc_info = {
                'document_name': doc_plan.get('document_name', 'Unknown'),
                'original_document_name': doc_plan.get('original_document_name', ''),
                'keywords': doc_plan.get('keywords', []),
                'summary': doc_plan.get('summary', ''),
                'main_topics': doc_plan.get('main_topics', []),
                'recommended_questions': doc_plan.get('recommended_questions', {})
            }
            documents_info.append(doc_info)
        
        return documents_info
    
    @staticmethod
    def calculate_extra_questions(keywords: List[str], max_objective: int = 6, max_subjective: int = 3) -> Tuple[int, int]:
        """키워드 수에 따른 여분 문제 수 계산"""
        extra_objective = min(len(keywords) * 2, max_objective)
        extra_subjective = min(len(keywords), max_subjective)
        return extra_objective, extra_subjective