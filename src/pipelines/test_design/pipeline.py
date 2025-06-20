"""
Test Design Pipeline
테스트 설계 에이전트만을 위한 독립적인 파이프라인

기능:
- 키워드 및 문서 요약 기반 테스트 요구사항 분석
- Gemini를 활용한 테스트 요약 생성
- 테스트 설정(config) 자동 생성
- 테스트 요약 및 설정 파일 저장
"""

import os
import json
import time
from typing import Dict, Any, List
from datetime import datetime
from src.agents.test_designer.agent import design_test_from_analysis


class TestDesignPipeline:
    """테스트 설계 전용 파이프라인"""
    
    def __init__(self, collection_name: str = None):
        """파이프라인 초기화"""
        self.collection_name = collection_name
    
    def run(
        self,
        keywords: List[str],
        document_summary: str,
        document_topics: List[str],
        user_prompt: str,
        difficulty: str = "medium",
        test_type: str = "mixed",
        time_limit: int = 60,
        save_results: bool = True
    ) -> Dict[str, Any]:
        """
        테스트 설계 파이프라인 실행
        
        Args:
            keywords: 문서 키워드 목록
            document_summary: 문서 요약
            document_topics: 주요 주제 목록
            user_prompt: 사용자 요청 프롬프트
            difficulty: 난이도 (easy, medium, hard)
            test_type: 테스트 유형 (objective, subjective, mixed)
            time_limit: 제한시간 (분)
            save_results: 결과 저장 여부
            
        Returns:
            Dict: 테스트 설계 결과
        """
        start_time = time.time()
        
        print("🎯 Test Design Pipeline 시작")
        print(f"📝 사용자 요청: {user_prompt}")
        print(f"🔑 키워드: {len(keywords)}개")
        print(f"📋 주제: {len(document_topics)}개")
        print(f"⚡ 난이도: {difficulty}")
        print(f"📊 테스트 유형: {test_type}")
        print(f"⏰ 제한시간: {time_limit}분")
        print("=" * 60)
        
        try:
            # 테스트 설계 실행
            print("\n🔄 테스트 요구사항 분석 중...")
            design_result = design_test_from_analysis(
                keywords=keywords,
                document_summary=document_summary,
                document_topics=document_topics,
                user_prompt=user_prompt,
                difficulty=difficulty,
                test_type=test_type,
                time_limit=time_limit
            )
            
            # 처리 시간 계산
            processing_time = time.time() - start_time
            
            # 결과 구성
            pipeline_result = {
                "pipeline_info": {
                    "pipeline_type": "test_design",
                    "user_prompt": user_prompt,
                    "difficulty": difficulty,
                    "test_type": test_type,
                    "time_limit": time_limit,
                    "keywords_count": len(keywords),
                    "topics_count": len(document_topics),
                    "processing_time": round(processing_time, 2),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "input_data": {
                    "keywords": keywords,
                    "document_summary": document_summary,
                    "document_topics": document_topics
                },
                "design_result": design_result,
                "status": "completed" if design_result else "failed"
            }
            
            # 결과 저장
            if save_results and design_result:
                saved_files = self._save_results(pipeline_result)
                pipeline_result["saved_files"] = saved_files
            
            # 결과 출력
            if design_result:
                test_config = design_result.get("test_config", {})
                print(f"\n✅ 테스트 설계 완료!")
                print(f"⏱️  처리 시간: {processing_time:.2f}초")
                print(f"📊 총 문제 수: {test_config.get('num_questions', 0)}개")
                print(f"   - 객관식: {test_config.get('num_objective', 0)}개")
                print(f"   - 주관식: {test_config.get('num_subjective', 0)}개")
                print(f"📋 테스트 요약: {len(design_result.get('test_summary', ''))}자")
                if save_results:
                    print(f"💾 저장된 파일: {len(pipeline_result.get('saved_files', []))}개")
            else:
                print(f"\n❌ 테스트 설계 실패!")
            
            return pipeline_result
            
        except Exception as e:
            print(f"❌ 테스트 설계 실패: {e}")
            return {
                "pipeline_info": {
                    "pipeline_type": "test_design",
                    "user_prompt": user_prompt,
                    "processing_time": round(time.time() - start_time, 2),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "input_data": {
                    "keywords": keywords,
                    "document_summary": document_summary,
                    "document_topics": document_topics
                },
                "design_result": {},
                "status": "failed",
                "error": str(e)
            }
    
    def run_from_keywords_file(
        self,
        keywords_file_path: str,
        user_prompt: str,
        difficulty: str = "medium",
        test_type: str = "mixed",
        time_limit: int = 60,
        save_results: bool = True
    ) -> Dict[str, Any]:
        """
        키워드 파일로부터 테스트 설계 실행
        
        Args:
            keywords_file_path: 키워드/요약 JSON 파일 경로
            user_prompt: 사용자 요청 프롬프트
            difficulty: 난이도
            test_type: 테스트 유형
            time_limit: 제한시간
            save_results: 결과 저장 여부
            
        Returns:
            Dict: 테스트 설계 결과
        """
        try:
            # 키워드 파일 로드
            with open(keywords_file_path, 'r', encoding='utf-8') as f:
                keywords_data = json.load(f)
            
            content_analysis = keywords_data.get('content_analysis', {})
            
            return self.run(
                keywords=content_analysis.get('keywords', []),
                document_summary=content_analysis.get('summary', ''),
                document_topics=content_analysis.get('main_topics', []),
                user_prompt=user_prompt,
                difficulty=difficulty,
                test_type=test_type,
                time_limit=time_limit,
                save_results=save_results
            )
            
        except Exception as e:
            print(f"❌ 키워드 파일 로딩 실패: {e}")
            return {
                "pipeline_info": {
                    "pipeline_type": "test_design",
                    "keywords_file": keywords_file_path,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "status": "failed",
                "error": f"키워드 파일 로딩 실패: {str(e)}"
            }
    
    def _save_results(self, pipeline_result: Dict[str, Any]) -> List[str]:
        """결과 파일 저장"""
        saved_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            design_result = pipeline_result["design_result"]
            
            # Collection 명 기반 디렉토리 구조
            collection_dir = self.collection_name or "default"
            
            # 테스트 요약 저장
            if design_result.get("test_summary"):
                summary_dir = f"data/outputs/test_summaries/{collection_dir}"
                os.makedirs(summary_dir, exist_ok=True)
                
                summary_data = {
                    "test_summary": design_result["test_summary"],
                    "pipeline_info": pipeline_result["pipeline_info"],
                    "input_data": pipeline_result["input_data"]
                }
                
                summary_file = f"{summary_dir}/test_summary_{timestamp}.json"
                with open(summary_file, 'w', encoding='utf-8') as f:
                    json.dump(summary_data, f, ensure_ascii=False, indent=2)
                saved_files.append(summary_file)
                print(f"💾 테스트 요약 저장: {summary_file}")
            
            # 테스트 설정 저장
            if design_result.get("test_config"):
                config_dir = f"data/outputs/test_configs/{collection_dir}"
                os.makedirs(config_dir, exist_ok=True)
                
                config_data = {
                    "test_config": design_result["test_config"],
                    "pipeline_info": pipeline_result["pipeline_info"]
                }
                
                config_file = f"{config_dir}/test_config_{timestamp}.json"
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                saved_files.append(config_file)
                print(f"💾 테스트 설정 저장: {config_file}")
            
            # test_design_results 파일은 제거 (test_summaries, test_configs만 저장)
            
        except Exception as e:
            print(f"⚠️ 결과 저장 실패: {e}")
        
        return saved_files


def run_test_design(
    keywords: List[str],
    document_summary: str,
    document_topics: List[str],
    user_prompt: str,
    difficulty: str = "medium",
    test_type: str = "mixed",
    time_limit: int = 60
) -> Dict[str, Any]:
    """
    테스트 설계 파이프라인 실행 편의 함수
    
    Args:
        keywords: 키워드 목록
        document_summary: 문서 요약
        document_topics: 주제 목록
        user_prompt: 사용자 요청
        difficulty: 난이도
        test_type: 테스트 유형
        time_limit: 제한시간
        
    Returns:
        Dict: 테스트 설계 결과
    """
    pipeline = TestDesignPipeline()
    return pipeline.run(keywords, document_summary, document_topics, user_prompt, difficulty, test_type, time_limit)


def run_test_design_from_file(
    keywords_file_path: str,
    user_prompt: str,
    difficulty: str = "medium"
) -> Dict[str, Any]:
    """
    키워드 파일로부터 테스트 설계 실행 편의 함수
    
    Args:
        keywords_file_path: 키워드 파일 경로
        user_prompt: 사용자 요청
        difficulty: 난이도
        
    Returns:
        Dict: 테스트 설계 결과
    """
    pipeline = TestDesignPipeline()
    return pipeline.run_from_keywords_file(keywords_file_path, user_prompt, difficulty)


if __name__ == "__main__":
    import glob
    import os
    
    print("🎯 Test Design Pipeline")
    print("=" * 50)
    
    # 사용 가능한 collection 목록 표시
    keywords_base_dir = "data/outputs/keywords_summary"
    if not os.path.exists(keywords_base_dir):
        print("❌ keywords_summary 디렉토리가 없습니다. 먼저 문서 분석을 실행하세요.")
        exit(1)
    
    collections = [d for d in os.listdir(keywords_base_dir) if os.path.isdir(os.path.join(keywords_base_dir, d))]
    if not collections:
        print("❌ 사용 가능한 collection이 없습니다. 먼저 문서 분석을 실행하세요.")
        exit(1)
    
    print("사용 가능한 Collection:")
    for i, collection in enumerate(collections, 1):
        # 해당 collection의 keywords 파일 개수 확인
        collection_dir = os.path.join(keywords_base_dir, collection)
        keyword_files = glob.glob(f"{collection_dir}/*_keywords_summary_*.json")
        print(f"  {i}. {collection} ({len(keyword_files)}개 키워드 파일)")
    
    # Collection 선택
    try:
        choice = int(input(f"\n사용할 Collection 번호를 선택하세요 (1-{len(collections)}): "))
        if 1 <= choice <= len(collections):
            selected_collection = collections[choice - 1]
            print(f"✅ 선택된 Collection: {selected_collection}")
        else:
            print("❌ 잘못된 번호입니다.")
            exit(1)
    except ValueError:
        print("❌ 숫자를 입력해주세요.")
        exit(1)
    
    # 해당 collection의 최신 키워드 파일 찾기
    collection_keywords_dir = os.path.join(keywords_base_dir, selected_collection)
    keyword_files = glob.glob(f"{collection_keywords_dir}/*_keywords_summary_*.json")
    
    if not keyword_files:
        print(f"❌ {selected_collection} collection에 키워드 파일이 없습니다.")
        exit(1)
    
    # 최신 파일 선택 (파일명의 timestamp 기준)
    latest_keywords_file = sorted(keyword_files)[-1]
    print(f"📄 사용할 키워드 파일: {os.path.basename(latest_keywords_file)}")
    
    # 사용자 프롬프트 입력
    print("\n테스트 요구사항을 입력하세요:")
    print("예시: '중급 난이도 테스트를 만들어주세요. 객관식 5문제, 주관식 3문제로 구성하고, 실무 적용 능력을 평가하는 문제를 포함해주세요.'")
    user_prompt = input(">>> ").strip()
    
    if not user_prompt:
        print("❌ 테스트 요구사항을 입력해주세요.")
        exit(1)
    
    # 난이도 선택
    print("\n난이도를 선택하세요:")
    print("  1. easy (쉬움)")
    print("  2. medium (보통)")
    print("  3. hard (어려움)")
    
    difficulty_map = {"1": "easy", "2": "medium", "3": "hard"}
    difficulty_choice = input("난이도 번호 (기본값: 2): ").strip()
    difficulty = difficulty_map.get(difficulty_choice, "medium")
    
    print(f"\n🔄 테스트 설계 시작...")
    print(f"📦 Collection: {selected_collection}")
    print(f"📄 키워드 파일: {os.path.basename(latest_keywords_file)}")
    print(f"📝 사용자 요청: {user_prompt}")
    print(f"⚡ 난이도: {difficulty}")
    
    # 파이프라인 실행
    pipeline = TestDesignPipeline(collection_name=selected_collection)
    result = pipeline.run_from_keywords_file(
        keywords_file_path=latest_keywords_file,
        user_prompt=user_prompt,
        difficulty=difficulty
    )
    print(f"\n최종 결과: {result['status']}")