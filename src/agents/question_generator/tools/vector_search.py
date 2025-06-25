"""
VectorDB 검색 관련 도구
"""

from typing import Dict, List, Any


class VectorSearchHandler:
    """VectorDB 검색 처리 클래스"""
    
    def __init__(self):
        self.searcher = None
        try:
            from db.vectorDB.chromaDB.search import ChromaDBSearcher
            self.searcher = ChromaDBSearcher()
            print("🔍 VectorDB 검색 핸들러 초기화 완료")
        except ImportError:
            print("⚠️ VectorDB 검색 기능을 사용할 수 없습니다.")
    
    def _convert_document_name_to_collection(self, document_name: str) -> str:
        """문서명을 collection명으로 변환"""
        if not document_name:
            return "unified_collection"
        
        # 이미 적절한 collection명인 경우 그대로 사용
        if document_name.startswith(('doc_', 'c_')) and '_' in document_name:
            return document_name
        
        # 우선 원본 이름 그대로 시도 (doc_ 접두사 없이)
        original_name = document_name
        
        # ChromaDB에서 실제 컬렉션 존재 여부 확인
        try:
            if self.searcher and hasattr(self.searcher, 'client'):
                collections = self.searcher.client.list_collections()
                collection_names = [c.name for c in collections]
                
                # 정확히 일치하는 컬렉션 찾기
                if original_name in collection_names:
                    print(f"📝 문서명 변환: '{document_name}' → '{original_name}' (정확 일치)")
                    return original_name
                
                # doc_ 접두사가 있는 버전 확인
                doc_prefixed = f"doc_{original_name}"
                if doc_prefixed in collection_names:
                    print(f"📝 문서명 변환: '{document_name}' → '{doc_prefixed}' (doc_ 접두사)")
                    return doc_prefixed
                
                # 부분 일치 검색
                partial_matches = [name for name in collection_names if original_name in name or name in original_name]
                if partial_matches:
                    best_match = partial_matches[0]
                    print(f"📝 문서명 변환: '{document_name}' → '{best_match}' (부분 일치)")
                    return best_match
                    
        except Exception as e:
            print(f"⚠️ 컬렉션 목록 확인 실패: {e}")
        
        # Fallback: 문서명 변환 로직
        import re
        
        # 특수문자 제거 및 소문자 변환
        clean_name = re.sub(r'[^a-zA-Z0-9가-힣_]', '_', document_name.lower())
        
        # 연속된 언더스코어 제거
        clean_name = re.sub(r'_+', '_', clean_name)
        
        # 앞뒤 언더스코어 제거
        clean_name = clean_name.strip('_')
        
        # 빈 문자열인 경우 기본값
        if not clean_name:
            return "unified_collection"
        
        print(f"📝 문서명 변환: '{document_name}' → '{clean_name}' (fallback)")
        return clean_name
    
    def search_keywords_in_collection(
        self, 
        keywords: List[str], 
        document_name: str, 
        max_results_per_keyword: int = 3
    ) -> List[Dict]:
        """문서명을 기반으로 컬렉션에서 키워드 관련 콘텐츠 검색"""
        if not self.searcher:
            print("⚠️ VectorDB에서 관련 문서 검색에 실패했습니다. 검색기가 초기화되지 않았습니다.")
            return []
        
        # 문서명을 collection명으로 변환
        collection_name = self._convert_document_name_to_collection(document_name)
        
        all_content = []
        
        for keyword in keywords[:5]:  # 상위 5개 키워드만 사용
            print(f"🔍 키워드 '{keyword}' 검색 중...")
            
            try:
                # 키워드로 유사도 검색
                results = self.searcher.search_similar(
                    query=keyword,
                    collection_name=collection_name,
                    n_results=max_results_per_keyword,
                    where=None
                )
                
                if results:
                    print(f"  ✅ 컬렉션 '{collection_name}'에서 {len(results)}개 결과 발견")
                    for result in results:
                        result['search_keyword'] = keyword
                        result['source_collection'] = collection_name
                        result['original_document_name'] = document_name
                    all_content.extend(results)
                else:
                    print(f"  ❌ 키워드 '{keyword}' 검색 결과 없음")
            
            except Exception as e:
                print(f"  ⚠️ 키워드 '{keyword}' 검색 실패: {e}")
                continue
        
        # 검색 결과가 없는 경우 fallback 시도
        if not all_content:
            print(f"⚠️ VectorDB에서 관련 문서 검색에 실패했습니다. 컬렉션 '{collection_name}'에서 검색 결과 없음. Fallback 컬렉션에서 재시도...")
            fallback_results = self.search_with_fallback_collections(
                keywords=keywords,
                primary_document_name=None  # 이미 실패했으므로 None
            )
            if fallback_results:
                print(f"✅ Fallback 검색으로 {len(fallback_results)}개 콘텐츠 발견")
                all_content.extend(fallback_results)
            else:
                print("⚠️ VectorDB에서 관련 문서 검색에 실패했습니다. 모든 컬렉션에서 검색 결과를 찾을 수 없습니다.")
        
        print(f"📊 총 {len(all_content)}개 관련 콘텐츠 발견")
        return all_content
    
    def search_with_fallback_collections(
        self, 
        keywords: List[str], 
        primary_document_name: str = None,
        fallback_collections: List[str] = None
    ) -> List[Dict]:
        """주 문서에서 검색 후 실패 시 대체 컬렉션에서 검색"""
        if not fallback_collections:
            fallback_collections = [
                "document_chunks",
                "unified_collection", 
                "skib_documents",
                "doc_2_ags_trouble_shooting_v1_1",
                "to_be_portal_process_fp_07_v1_0"
            ]
        
        # 주 문서명이 지정된 경우 먼저 시도
        if primary_document_name:
            content = self.search_keywords_in_collection(keywords, primary_document_name)
            if content:
                return content
        
        # 대체 컬렉션들에서 직접 검색 (이미 collection명인 경우)
        primary_collection = self._convert_document_name_to_collection(primary_document_name) if primary_document_name else None
        
        for collection in fallback_collections:
            if collection == primary_collection:
                continue  # 이미 시도한 컬렉션은 스킵
            
            try:
                # 대체 컬렉션에서 직접 검색
                content = self._search_in_specific_collection(keywords, collection)
                if content:
                    return content
            except Exception as e:
                print(f"  ⚠️ 컬렉션 '{collection}' 검색 실패: {e}")
                continue
        
        return []
    
    def _search_in_specific_collection(self, keywords: List[str], collection_name: str, max_results_per_keyword: int = 3) -> List[Dict]:
        """특정 컬렉션에서 직접 검색 (변환 없이)"""
        if not self.searcher:
            print("⚠️ VectorDB에서 관련 문서 검색에 실패했습니다. 검색기가 사용할 수 없습니다.")
            return []
        
        all_content = []
        
        for keyword in keywords[:5]:
            try:
                results = self.searcher.search_similar(
                    query=keyword,
                    collection_name=collection_name,
                    n_results=max_results_per_keyword,
                    where=None
                )
                
                if results:
                    print(f"  ✅ 대체 컬렉션 '{collection_name}'에서 {len(results)}개 결과 발견")
                    for result in results:
                        result['search_keyword'] = keyword
                        result['source_collection'] = collection_name
                        result['is_fallback'] = True
                    all_content.extend(results)
            except Exception as e:
                print(f"  ⚠️ 키워드 '{keyword}' 검색 실패: {e}")
                continue
        
        return all_content
    
    def convert_content_to_blocks(self, related_content: List[Dict], keywords: List[str]) -> List[Dict]:
        """관련 콘텐츠를 블록 형태로 변환"""
        blocks = []
        
        # 키워드 정보를 포함한 헤더 블록 추가
        header_content = f"🔑 핵심 키워드: {', '.join(keywords)}\n\n"
        blocks.append({
            "type": "heading",
            "content": header_content,
            "metadata": {"page": 1, "source": "keyword_context"}
        })
        
        # 관련 콘텐츠를 블록으로 변환
        for i, content in enumerate(related_content[:10]):  # 상위 10개만 사용
            block = {
                "type": "paragraph",
                "content": content.get('content', ''),
                "metadata": {
                    "page": i + 1,
                    "source": content.get('source_collection', 'vector_search'),
                    "search_keyword": content.get('search_keyword', ''),
                    "similarity": content.get('similarity', 0.0)
                }
            }
            blocks.append(block)
        
        return blocks