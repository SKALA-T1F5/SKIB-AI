"""
Question Generation Pipeline
문제 생성 에이전트만을 위한 독립적인 파이프라인

기능:
- 파싱된 블록(텍스트, 이미지, 표)을 사용한 문제 생성
- Gemini Vision을 활용한 이미지 기반 문제 생성
- 테스트 설정에 따른 맞춤형 문제 생성
- 생성된 문제 저장 및 관리
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.agents.question_generator.agent import QuestionGeneratorAgent


class QuestionGenerationPipeline:
    """문제 생성 전용 파이프라인"""
    
    def __init__(self, collection_name: str = None):
        """
        파이프라인 초기화
        
        Args:
            collection_name: 컬렉션명 (이미지 경로 결정)
        """
        self.collection_name = collection_name
        self.question_generator = None
    
    def run(
        self,
        blocks: List[Dict],
        num_objective: int = 5,
        num_subjective: int = 3,
        source_file: str = "document.pdf",
        keywords: List[str] = None,
        main_topics: List[str] = None,
        summary: str = "",
        test_config: Dict[str, Any] = None,
        save_results: bool = True
    ) -> Dict[str, Any]:
        """
        문제 생성 파이프라인 실행
        
        Args:
            blocks: 문서 블록들 (파싱된 텍스트, 이미지, 표)
            num_objective: 객관식 문제 수
            num_subjective: 주관식 문제 수
            source_file: 원본 파일명
            keywords: 키워드 목록
            main_topics: 주요 주제 목록
            summary: 문서 요약
            test_config: 테스트 설정 (옵션)
            save_results: 결과 저장 여부
            
        Returns:
            Dict: 문제 생성 결과
        """
        start_time = time.time()
        
        print("🤖 Question Generation Pipeline 시작")
        print(f"📄 원본 파일: {source_file}")
        print(f"📦 컬렉션: {self.collection_name or 'default'}")
        print(f"📝 총 블록: {len(blocks)}개")
        print(f"🎯 목표 문제: 객관식 {num_objective}개, 주관식 {num_subjective}개")
        if keywords:
            print(f"🔑 키워드: {len(keywords)}개")
        if main_topics:
            print(f"📋 주제: {len(main_topics)}개")
        print("=" * 60)
        
        try:
            # QuestionGenerator 초기화
            self.question_generator = QuestionGeneratorAgent(self.collection_name)
            
            # 문제 생성 실행
            print("\n🔄 GPT-4 Vision으로 문제 생성 중...")
            print(f"🔍 VectorDB 검색: {'활성화' if self.collection_name else '비활성화'}")
            generation_result = self.question_generator.generate_questions_from_blocks(
                blocks=blocks,
                num_objective=num_objective,
                num_subjective=num_subjective,
                source_file=source_file,
                keywords=keywords or [],
                main_topics=main_topics or [],
                summary=summary,
                test_config=test_config,
                use_vectordb_search=bool(self.collection_name)
            )
            
            # 처리 시간 계산
            processing_time = time.time() - start_time
            
            # 결과 구성
            pipeline_result = {
                "pipeline_info": {
                    "pipeline_type": "question_generation",
                    "source_file": source_file,
                    "collection_name": self.collection_name,
                    "total_blocks": len(blocks),
                    "target_objective": num_objective,
                    "target_subjective": num_subjective,
                    "processing_time": round(processing_time, 2),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "input_data": {
                    "blocks_count": len(blocks),
                    "blocks_breakdown": self._analyze_blocks(blocks),
                    "keywords": keywords or [],
                    "main_topics": main_topics or [],
                    "summary": summary,
                    "test_config": test_config
                },
                "generation_result": generation_result,
                "status": generation_result.get("status", "unknown")
            }
            
            # 결과 저장
            if save_results and generation_result.get("status") == "completed":
                saved_files = self._save_results(pipeline_result)
                pipeline_result["saved_files"] = saved_files
            
            # 결과 출력
            if generation_result.get("status") == "completed":
                print(f"\n✅ 문제 생성 완료!")
                print(f"⏱️  처리 시간: {processing_time:.2f}초")
                print(f"📊 생성된 문제: {generation_result.get('total_questions', 0)}개")
                print(f"   - 객관식: {generation_result.get('objective_count', 0)}개")
                print(f"   - 주관식: {generation_result.get('subjective_count', 0)}개")
                if save_results:
                    print(f"💾 저장된 파일: {len(pipeline_result.get('saved_files', []))}개")
            else:
                print(f"\n❌ 문제 생성 실패!")
                if generation_result.get("error"):
                    print(f"오류: {generation_result['error']}")
            
            return pipeline_result
            
        except Exception as e:
            print(f"❌ 문제 생성 실패: {e}")
            return {
                "pipeline_info": {
                    "pipeline_type": "question_generation",
                    "source_file": source_file,
                    "collection_name": self.collection_name,
                    "processing_time": round(time.time() - start_time, 2),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "input_data": {
                    "blocks_count": len(blocks),
                    "keywords": keywords or [],
                    "main_topics": main_topics or []
                },
                "generation_result": {},
                "status": "failed",
                "error": str(e)
            }
    
    def run_from_analysis_result(
        self,
        analysis_result_file: str,
        num_objective: int = 5,
        num_subjective: int = 3,
        test_config_file: str = None,
        save_results: bool = True
    ) -> Dict[str, Any]:
        """
        문서 분석 결과 파일로부터 문제 생성 실행
        
        Args:
            analysis_result_file: 문서 분석 결과 JSON 파일 경로
            num_objective: 객관식 문제 수
            num_subjective: 주관식 문제 수
            test_config_file: 테스트 설정 파일 경로 (옵션)
            save_results: 결과 저장 여부
            
        Returns:
            Dict: 문제 생성 결과
        """
        try:
            # 분석 결과 로드
            with open(analysis_result_file, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
            
            analysis_result = analysis_data.get('analysis_result', {})
            
            # 테스트 설정 로드 (옵션)
            test_config = None
            if test_config_file and os.path.exists(test_config_file):
                with open(test_config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    test_config = config_data.get('test_config', {})
                    
                    # 테스트 설정에서 문제 수 가져오기
                    if 'num_objective' in test_config:
                        num_objective = test_config['num_objective']
                    if 'num_subjective' in test_config:
                        num_subjective = test_config['num_subjective']
            
            # 컬렉션명 설정
            pipeline_info = analysis_data.get('pipeline_info', {})
            collection_name = pipeline_info.get('collection_name')
            if collection_name:
                self.collection_name = collection_name
            
            return self.run(
                blocks=analysis_result.get('blocks', []),
                num_objective=num_objective,
                num_subjective=num_subjective,
                source_file=pipeline_info.get('pdf_path', 'document.pdf'),
                keywords=analysis_result.get('keywords', []),
                main_topics=analysis_result.get('main_topics', []),
                summary=analysis_result.get('summary', ''),
                test_config=test_config,
                save_results=save_results
            )
            
        except Exception as e:
            print(f"❌ 분석 결과 파일 로딩 실패: {e}")
            return {
                "pipeline_info": {
                    "pipeline_type": "question_generation",
                    "analysis_file": analysis_result_file,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "status": "failed",
                "error": f"분석 결과 파일 로딩 실패: {str(e)}"
            }
    
    def _analyze_blocks(self, blocks: List[Dict]) -> Dict[str, int]:
        """블록 유형별 분석"""
        breakdown = {"text": 0, "table": 0, "image": 0, "other": 0}
        
        for block in blocks:
            block_type = block.get("type", "other")
            if block_type in ["paragraph", "heading", "section"]:
                breakdown["text"] += 1
            elif block_type == "table":
                breakdown["table"] += 1
            elif block_type == "image":
                breakdown["image"] += 1
            else:
                breakdown["other"] += 1
        
        return breakdown
    
    def _save_results(self, pipeline_result: Dict[str, Any]) -> List[str]:
        """결과 파일 저장"""
        saved_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        source_name = os.path.splitext(os.path.basename(
            pipeline_result["pipeline_info"]["source_file"]
        ))[0]
        
        try:
            generation_result = pipeline_result["generation_result"]
            
            # Collection 명 기반 디렉토리 구조
            collection_dir = self.collection_name or "default"
            
            # 생성된 문제 저장
            if generation_result.get("questions"):
                questions_dir = f"data/outputs/generated_questions/{collection_dir}"
                os.makedirs(questions_dir, exist_ok=True)
                
                questions_data = {
                    "test_info": {
                        "source_file": pipeline_result["pipeline_info"]["source_file"],
                        "collection_name": pipeline_result["pipeline_info"]["collection_name"],
                        "generation_date": datetime.now().isoformat(),
                        "test_type": "auto_generated"
                    },
                    "question_summary": {
                        "total_questions": len(generation_result["questions"]),
                        "objective_questions": generation_result.get("objective_count", 0),
                        "subjective_questions": generation_result.get("subjective_count", 0)
                    },
                    "questions": generation_result["questions"],
                    "pipeline_info": pipeline_result["pipeline_info"],
                    "input_data": pipeline_result["input_data"]
                }
                
                questions_file = f"{questions_dir}/{source_name}_questions_{timestamp}.json"
                with open(questions_file, 'w', encoding='utf-8') as f:
                    json.dump(questions_data, f, ensure_ascii=False, indent=2)
                saved_files.append(questions_file)
                print(f"💾 생성된 문제 저장: {questions_file}")
            
            # 전체 결과 저장
            results_dir = "data/outputs/question_generation_results"
            os.makedirs(results_dir, exist_ok=True)
            
            result_file = f"{results_dir}/{source_name}_question_generation_{timestamp}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(pipeline_result, f, ensure_ascii=False, indent=2)
            saved_files.append(result_file)
            print(f"💾 전체 결과 저장: {result_file}")
            
        except Exception as e:
            print(f"⚠️ 결과 저장 실패: {e}")
        
        return saved_files


def run_question_generation(
    blocks: List[Dict],
    num_objective: int = 5,
    num_subjective: int = 3,
    collection_name: str = None,
    source_file: str = "document.pdf"
) -> Dict[str, Any]:
    """
    문제 생성 파이프라인 실행 편의 함수
    
    Args:
        blocks: 문서 블록들
        num_objective: 객관식 문제 수
        num_subjective: 주관식 문제 수
        collection_name: 컬렉션명
        source_file: 원본 파일명
        
    Returns:
        Dict: 문제 생성 결과
    """
    pipeline = QuestionGenerationPipeline(collection_name)
    return pipeline.run(blocks, num_objective, num_subjective, source_file)


def run_question_generation_from_file(
    analysis_result_file: str,
    num_objective: int = 5,
    num_subjective: int = 3,
    test_config_file: str = None
) -> Dict[str, Any]:
    """
    분석 결과 파일로부터 문제 생성 실행 편의 함수
    
    Args:
        analysis_result_file: 문서 분석 결과 파일 경로
        num_objective: 객관식 문제 수
        num_subjective: 주관식 문제 수
        test_config_file: 테스트 설정 파일 경로
        
    Returns:
        Dict: 문제 생성 결과
    """
    pipeline = QuestionGenerationPipeline()
    return pipeline.run_from_analysis_result(
        analysis_result_file, num_objective, num_subjective, test_config_file
    )


if __name__ == "__main__":
    import glob
    import os
    import json
    
    print("🤖 Question Generation Pipeline")
    print("=" * 50)
    
    # 사용 가능한 collection 목록 표시
    keywords_base_dir = "data/outputs/keywords_summary"
    configs_base_dir = "data/outputs/test_configs"
    analysis_base_dir = "data/outputs/document_analysis"
    
    if not os.path.exists(keywords_base_dir):
        print("❌ keywords_summary 디렉토리가 없습니다. 먼저 문서 분석을 실행하세요.")
        exit(1)
    
    collections = [d for d in os.listdir(keywords_base_dir) if os.path.isdir(os.path.join(keywords_base_dir, d))]
    if not collections:
        print("❌ 사용 가능한 collection이 없습니다. 먼저 문서 분석을 실행하세요.")
        exit(1)
    
    print("사용 가능한 Collection:")
    for i, collection in enumerate(collections, 1):
        # 키워드, 테스트 설정, 분석 결과 파일 개수 확인
        keyword_files = glob.glob(f"{keywords_base_dir}/{collection}/*_keywords_summary_*.json")
        config_files = glob.glob(f"{configs_base_dir}/{collection}/*_test_config_*.json") if os.path.exists(f"{configs_base_dir}/{collection}") else []
        analysis_files = glob.glob(f"{analysis_base_dir}/{collection}/*_analysis_result_*.json") if os.path.exists(f"{analysis_base_dir}/{collection}") else []
        print(f"  {i}. {collection} (키워드: {len(keyword_files)}개, 테스트설정: {len(config_files)}개, 분석결과: {len(analysis_files)}개)")
    
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
    
    # 키워드 파일 찾기
    collection_keywords_dir = os.path.join(keywords_base_dir, selected_collection)
    keyword_files = glob.glob(f"{collection_keywords_dir}/*_keywords_summary_*.json")
    
    if not keyword_files:
        print(f"❌ {selected_collection} collection에 키워드 파일이 없습니다.")
        exit(1)
    
    latest_keywords_file = sorted(keyword_files)[-1]
    print(f"📄 키워드 파일: {os.path.basename(latest_keywords_file)}")
    
    # 테스트 설정 파일 찾기 (선택적)
    collection_configs_dir = os.path.join(configs_base_dir, selected_collection)
    config_file = None
    if os.path.exists(collection_configs_dir):
        config_files = glob.glob(f"{collection_configs_dir}/*_test_config_*.json")
        if config_files:
            config_file = sorted(config_files)[-1]
            print(f"⚙️ 테스트 설정 파일: {os.path.basename(config_file)}")
        else:
            print("⚠️ 테스트 설정 파일이 없습니다. 기본 설정을 사용합니다.")
    else:
        print("⚠️ 테스트 설정 파일이 없습니다. 먼저 테스트 설계를 실행하세요.")
    
    # 문제 수 입력
    print("\n문제 생성 설정:")
    try:
        num_objective = int(input("객관식 문제 수 (기본값: 5): ") or "5")
        num_subjective = int(input("주관식 문제 수 (기본값: 3): ") or "3")
    except ValueError:
        print("❌ 숫자를 입력해주세요.")
        exit(1)
    
    print(f"\n🔄 문제 생성 시작...")
    print(f"📦 Collection: {selected_collection}")
    print(f"🎯 목표: 객관식 {num_objective}개, 주관식 {num_subjective}개")
    print(f"🔍 VectorDB 검색: 활성화")
    
    # 분석 결과 파일에서 블록 데이터 로드
    try:
        # 키워드 파일 로드
        with open(latest_keywords_file, 'r', encoding='utf-8') as f:
            keywords_data = json.load(f)
        content_analysis = keywords_data.get('content_analysis', {})
        
        # 분석 결과 파일 찾기
        collection_analysis_dir = os.path.join(analysis_base_dir, selected_collection)
        blocks = []
        
        if os.path.exists(collection_analysis_dir):
            analysis_files = glob.glob(f"{collection_analysis_dir}/*_analysis_result_*.json")
            if analysis_files:
                latest_analysis_file = sorted(analysis_files)[-1]
                print(f"📊 분석 결과 파일: {os.path.basename(latest_analysis_file)}")
                
                with open(latest_analysis_file, 'r', encoding='utf-8') as f:
                    analysis_data = json.load(f)
                
                analysis_result = analysis_data.get('analysis_result', {})
                blocks = analysis_result.get('blocks', [])
                
                if not blocks:
                    print("⚠️ 블록 데이터가 없습니다. 기본 블록을 생성합니다.")
                    blocks = [
                        {
                            'type': 'paragraph',
                            'content': f"문서 요약: {content_analysis.get('summary', '')}",
                            'metadata': {'page': 1, 'source': 'keywords_summary'}
                        }
                    ]
            else:
                print("⚠️ 분석 결과 파일이 없습니다. 기본 블록을 생성합니다.")
                blocks = [
                    {
                        'type': 'paragraph',
                        'content': f"문서 요약: {content_analysis.get('summary', '')}",
                        'metadata': {'page': 1, 'source': 'keywords_summary'}
                    }
                ]
        else:
            print("⚠️ 분석 결과 디렉토리가 없습니다. 기본 블록을 생성합니다.")
            blocks = [
                {
                    'type': 'paragraph',
                    'content': f"문서 요약: {content_analysis.get('summary', '')}",
                    'metadata': {'page': 1, 'source': 'keywords_summary'}
                }
            ]
        
        print(f"📝 사용할 블록: {len(blocks)}개")
        
        # 파이프라인 실행
        pipeline = QuestionGenerationPipeline(collection_name=selected_collection)
        result = pipeline.run(
            blocks=blocks,
            num_objective=num_objective,
            num_subjective=num_subjective,
            source_file=keywords_data.get('document_info', {}).get('source_file', 'document.pdf'),
            keywords=content_analysis.get('keywords', []),
            main_topics=content_analysis.get('main_topics', []),
            summary=content_analysis.get('summary', ''),
            test_config=json.load(open(config_file, 'r', encoding='utf-8')).get('test_config') if config_file else None
        )
        
        print(f"\n최종 결과: {result['status']}")
        
    except Exception as e:
        print(f"❌ 문제 생성 실패: {e}")