"""
Document Analysis Pipeline
문서 분석 에이전트만을 위한 독립적인 파이프라인

기능:
- PDF 문서 파싱 (텍스트, 이미지, 표)
- 키워드 추출 및 문서 요약
- ChromaDB 업로드
"""

import os
import time
from typing import Dict, Any, Optional
from src.agents.document_analyzer.agent import DocumentAnalyzerAgent
from utils.change_name import normalize_collection_name


class DocumentAnalysisPipeline:
    """문서 분석 전용 파이프라인"""
    
    def __init__(self, collection_name: str = None, auto_upload_chromadb: bool = True):
        """
        파이프라인 초기화
        
        Args:
            collection_name: ChromaDB 컬렉션명
            auto_upload_chromadb: ChromaDB 자동 업로드 여부
        """
        self.collection_name = collection_name
        self.auto_upload_chromadb = auto_upload_chromadb
        self.analyzer = None
    
    def run(
        self, 
        pdf_path: str, 
        extract_keywords: bool = True,
        collection_name: str = None
    ) -> Dict[str, Any]:
        """
        문서 분석 파이프라인 실행
        
        Args:
            pdf_path: 분석할 PDF 파일 경로
            extract_keywords: 키워드 추출 여부
            collection_name: 컬렉션명 (초기화 시 설정한 값 우선)
            
        Returns:
            Dict: 문서 분석 결과
        """
        start_time = time.time()
        
        # 컬렉션명 설정
        final_collection_name = collection_name or self.collection_name
        if not final_collection_name:
            filename = os.path.splitext(os.path.basename(pdf_path))[0]
            final_collection_name = normalize_collection_name(filename)
        
        print("🔄 Document Analysis Pipeline 시작")
        print(f"📄 문서: {pdf_path}")
        print(f"📦 컬렉션: {final_collection_name}")
        print(f"🔑 키워드 추출: {'활성화' if extract_keywords else '비활성화'}")
        print(f"💾 ChromaDB 업로드: {'활성화' if self.auto_upload_chromadb else '비활성화'}")
        print("=" * 60)
        
        try:
            # DocumentAnalyzer 초기화 및 실행
            self.analyzer = DocumentAnalyzerAgent(
                collection_name=final_collection_name,
                auto_upload_chromadb=self.auto_upload_chromadb
            )
            
            # 문서 분석 실행
            result = self.analyzer.analyze_document(pdf_path, extract_keywords)
            
            # 처리 시간 계산
            processing_time = time.time() - start_time
            
            # 결과 구성
            pipeline_result = {
                "pipeline_info": {
                    "pipeline_type": "document_analysis",
                    "pdf_path": pdf_path,
                    "collection_name": final_collection_name,
                    "extract_keywords": extract_keywords,
                    "auto_upload_chromadb": self.auto_upload_chromadb,
                    "processing_time": round(processing_time, 2),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "analysis_result": result,
                "status": result.get("processing_status", "unknown")
            }
            
            # 결과 출력
            print(f"\n✅ 문서 분석 완료!")
            print(f"⏱️  처리 시간: {processing_time:.2f}초")
            print(f"📊 분석 상태: {result.get('processing_status')}")
            print(f"📝 총 블록: {result.get('total_blocks', 0)}개")
            if extract_keywords:
                print(f"🔑 키워드: {len(result.get('keywords', []))}개")
                print(f"📋 주제: {len(result.get('main_topics', []))}개")
            if self.auto_upload_chromadb:
                print(f"💾 ChromaDB: {result.get('chromadb_upload_count', 0)}개 청크 업로드")
            
            return pipeline_result
            
        except Exception as e:
            print(f"❌ 문서 분석 실패: {e}")
            return {
                "pipeline_info": {
                    "pipeline_type": "document_analysis",
                    "pdf_path": pdf_path,
                    "collection_name": final_collection_name,
                    "processing_time": round(time.time() - start_time, 2),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                },
                "analysis_result": {},
                "status": "failed",
                "error": str(e)
            }


def run_document_analysis(
    pdf_path: str,
    collection_name: str = None,
    extract_keywords: bool = True,
    auto_upload_chromadb: bool = True
) -> Dict[str, Any]:
    """
    문서 분석 파이프라인 실행 편의 함수
    
    Args:
        pdf_path: PDF 파일 경로
        collection_name: 컬렉션명
        extract_keywords: 키워드 추출 여부
        auto_upload_chromadb: ChromaDB 자동 업로드 여부
        
    Returns:
        Dict: 분석 결과
    """
    pipeline = DocumentAnalysisPipeline(collection_name, auto_upload_chromadb)
    return pipeline.run(pdf_path, extract_keywords)


if __name__ == "__main__":
    import glob
    
    print("📄 Document Analysis Pipeline")
    print("=" * 50)
    
    # 사용 가능한 문서 목록 표시
    pdf_files = glob.glob("data/raw_docs/*.pdf")
    if not pdf_files:
        print("❌ data/raw_docs/ 디렉토리에 PDF 파일이 없습니다.")
        exit(1)
    
    print("사용 가능한 문서:")
    for i, pdf_file in enumerate(pdf_files, 1):
        filename = pdf_file.split('/')[-1]
        print(f"  {i}. {filename}")
    
    # 문서 선택
    try:
        choice = int(input(f"\n분석할 문서 번호를 선택하세요 (1-{len(pdf_files)}): "))
        if 1 <= choice <= len(pdf_files):
            selected_pdf = pdf_files[choice - 1]
            print(f"✅ 선택된 문서: {selected_pdf.split('/')[-1]}")
        else:
            print("❌ 잘못된 번호입니다.")
            exit(1)
    except ValueError:
        print("❌ 숫자를 입력해주세요.")
        exit(1)
    
    # Collection 명 입력
    default_collection = selected_pdf.split('/')[-1].replace('.pdf', '').replace(' ', '_').lower()
    collection_name = input(f"\nCollection 명을 입력하세요 (기본값: {default_collection}): ").strip()
    if not collection_name:
        collection_name = default_collection
    
    # 옵션 설정
    extract_keywords = input("키워드 추출을 하시겠습니까? (y/N): ").strip().lower() in ['y', 'yes']
    auto_upload = input("ChromaDB 자동 업로드를 하시겠습니까? (y/N): ").strip().lower() in ['y', 'yes']
    
    print(f"\n🔄 문서 분석 시작...")
    print(f"📄 문서: {selected_pdf}")
    print(f"📦 Collection: {collection_name}")
    print(f"🔑 키워드 추출: {'활성화' if extract_keywords else '비활성화'}")
    print(f"💾 ChromaDB 업로드: {'활성화' if auto_upload else '비활성화'}")
    
    result = run_document_analysis(
        pdf_path=selected_pdf,
        collection_name=collection_name,
        extract_keywords=extract_keywords,
        auto_upload_chromadb=auto_upload
    )
    print(f"\n최종 결과: {result['status']}")