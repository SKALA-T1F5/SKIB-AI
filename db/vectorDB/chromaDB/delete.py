"""
ChromaDB 컬렉션 삭제 관리 모듈
"""

import logging
from typing import List, Dict, Any, Optional
from .client import get_client
from .utils import list_collections, get_collection_info

logger = logging.getLogger(__name__)


class ChromaDBDeleter:
    """ChromaDB 컬렉션 삭제 관리 클래스"""
    
    def __init__(self):
        """삭제 관리자 초기화"""
        self.client = get_client()
        logger.info("🗑️ ChromaDB 삭제 관리자 초기화")
    
    def delete_collection(self, collection_name: str, force: bool = False) -> bool:
        """
        컬렉션 삭제
        
        Args:
            collection_name: 삭제할 컬렉션 이름
            force: 강제 삭제 여부 (확인 없이 삭제)
            
        Returns:
            삭제 성공 여부
        """
        try:
            # 컬렉션 존재 확인
            collections = list_collections()
            if collection_name not in collections:
                logger.warning(f"⚠️ 컬렉션 '{collection_name}'이 존재하지 않습니다")
                return False
            
            # 컬렉션 정보 조회
            info = self.get_collection_info_safe(collection_name)
            doc_count = info.get('count', 0)
            
            logger.info(f"🗑️ 컬렉션 '{collection_name}' 삭제 시작 (문서 {doc_count}개)")
            
            # 강제 삭제가 아닌 경우 확인
            if not force:
                logger.warning(f"⚠️ 확인 없이 삭제하려면 force=True 사용")
                return False
            
            # 삭제 실행
            self.client.get_client().delete_collection(name=collection_name)
            
            # 삭제 확인
            remaining_collections = list_collections()
            if collection_name not in remaining_collections:
                logger.info(f"✅ 컬렉션 '{collection_name}' 삭제 완료")
                return True
            else:
                logger.error(f"❌ 컬렉션 '{collection_name}' 삭제 실패 (여전히 존재)")
                return False
                
        except Exception as e:
            logger.error(f"❌ 컬렉션 '{collection_name}' 삭제 중 오류: {e}")
            return False
    
    def delete_multiple_collections(
        self, 
        collection_names: List[str], 
        force: bool = False
    ) -> Dict[str, bool]:
        """
        여러 컬렉션 일괄 삭제
        
        Args:
            collection_names: 삭제할 컬렉션 이름 리스트
            force: 강제 삭제 여부
            
        Returns:
            컬렉션별 삭제 결과 딕셔너리
        """
        results = {}
        
        logger.info(f"🗑️ 일괄 삭제 시작: {len(collection_names)}개 컬렉션")
        
        for collection_name in collection_names:
            try:
                success = self.delete_collection(collection_name, force=force)
                results[collection_name] = success
                
            except Exception as e:
                logger.error(f"❌ 컬렉션 '{collection_name}' 삭제 실패: {e}")
                results[collection_name] = False
        
        # 결과 요약
        successful = sum(1 for success in results.values() if success)
        logger.info(f"📊 일괄 삭제 완료: {successful}/{len(collection_names)}개 성공")
        
        return results
    
    def delete_empty_collections(self, force: bool = False) -> Dict[str, bool]:
        """
        빈 컬렉션들 삭제
        
        Args:
            force: 강제 삭제 여부
            
        Returns:
            삭제 결과 딕셔너리
        """
        empty_collections = []
        
        # 빈 컬렉션 찾기
        collections = list_collections()
        for collection_name in collections:
            try:
                info = self.get_collection_info_safe(collection_name)
                if info.get('count', 0) == 0:
                    empty_collections.append(collection_name)
            except:
                continue
        
        if not empty_collections:
            logger.info("📭 삭제할 빈 컬렉션이 없습니다")
            return {}
        
        logger.info(f"🗑️ 빈 컬렉션 {len(empty_collections)}개 발견: {empty_collections}")
        
        return self.delete_multiple_collections(empty_collections, force=force)
    
    def delete_collections_by_pattern(
        self, 
        pattern: str, 
        force: bool = False
    ) -> Dict[str, bool]:
        """
        패턴에 맞는 컬렉션들 삭제
        
        Args:
            pattern: 삭제할 컬렉션 이름 패턴 (부분 문자열)
            force: 강제 삭제 여부
            
        Returns:
            삭제 결과 딕셔너리
        """
        matching_collections = []
        
        # 패턴에 맞는 컬렉션 찾기
        collections = list_collections()
        for collection_name in collections:
            if pattern in collection_name:
                matching_collections.append(collection_name)
        
        if not matching_collections:
            logger.info(f"📭 패턴 '{pattern}'에 맞는 컬렉션이 없습니다")
            return {}
        
        logger.info(f"🔍 패턴 '{pattern}'에 맞는 컬렉션 {len(matching_collections)}개: {matching_collections}")
        
        return self.delete_multiple_collections(matching_collections, force=force)
    
    def get_collection_info_safe(self, collection_name: str) -> Dict[str, Any]:
        """안전한 컬렉션 정보 조회 (오류 시 기본값 반환)"""
        try:
            return get_collection_info(collection_name)
        except Exception as e:
            logger.warning(f"⚠️ 컬렉션 '{collection_name}' 정보 조회 실패: {e}")
            return {'count': 0, 'stats': {}}
    
    def get_deletion_preview(self, collection_names: List[str]) -> Dict[str, Any]:
        """
        삭제 미리보기 정보
        
        Args:
            collection_names: 삭제 예정 컬렉션 리스트
            
        Returns:
            삭제 미리보기 정보
        """
        preview = {
            'collections': [],
            'total_documents': 0,
            'total_collections': len(collection_names),
            'existing_collections': 0,
            'missing_collections': []
        }
        
        existing_collections = list_collections()
        
        for collection_name in collection_names:
            if collection_name not in existing_collections:
                preview['missing_collections'].append(collection_name)
                continue
            
            preview['existing_collections'] += 1
            
            try:
                info = self.get_collection_info_safe(collection_name)
                doc_count = info.get('count', 0)
                stats = info.get('stats', {})
                
                collection_info = {
                    'name': collection_name,
                    'document_count': doc_count,
                    'types': stats.get('types', {}),
                    'sources': list(stats.get('sources', {}).keys())
                }
                
                preview['collections'].append(collection_info)
                preview['total_documents'] += doc_count
                
            except Exception as e:
                logger.warning(f"⚠️ 컬렉션 '{collection_name}' 정보 조회 실패: {e}")
        
        return preview
    
    def clear_all_collections(self, force: bool = False) -> Dict[str, bool]:
        """
        모든 컬렉션 삭제 (매우 위험!)
        
        Args:
            force: 강제 삭제 여부
            
        Returns:
            삭제 결과 딕셔너리
        """
        if not force:
            logger.error("❌ 모든 컬렉션 삭제는 force=True가 필요합니다")
            return {}
        
        collections = list_collections()
        
        if not collections:
            logger.info("📭 삭제할 컬렉션이 없습니다")
            return {}
        
        logger.warning(f"⚠️ 모든 컬렉션 삭제 시작: {len(collections)}개")
        
        return self.delete_multiple_collections(collections, force=True)


# 편의 함수들
def delete_collection(collection_name: str, force: bool = False) -> bool:
    """컬렉션 삭제 편의 함수"""
    deleter = ChromaDBDeleter()
    return deleter.delete_collection(collection_name, force=force)


def delete_multiple_collections(collection_names: List[str], force: bool = False) -> Dict[str, bool]:
    """여러 컬렉션 삭제 편의 함수"""
    deleter = ChromaDBDeleter()
    return deleter.delete_multiple_collections(collection_names, force=force)


def delete_empty_collections(force: bool = False) -> Dict[str, bool]:
    """빈 컬렉션 삭제 편의 함수"""
    deleter = ChromaDBDeleter()
    return deleter.delete_empty_collections(force=force)


def delete_test_collections(force: bool = False) -> Dict[str, bool]:
    """테스트 컬렉션 삭제 편의 함수"""
    deleter = ChromaDBDeleter()
    return deleter.delete_collections_by_pattern("test", force=force)


def get_deletion_preview(collection_names: List[str]) -> Dict[str, Any]:
    """삭제 미리보기 편의 함수"""
    deleter = ChromaDBDeleter()
    return deleter.get_deletion_preview(collection_names)


def show_deletion_preview(collection_names: List[str]):
    """삭제 미리보기 출력"""
    preview = get_deletion_preview(collection_names)
    
    print("🗑️ 삭제 미리보기")
    print("=" * 50)
    print(f"📊 총 {preview['total_collections']}개 컬렉션 삭제 예정")
    print(f"📄 총 {preview['total_documents']}개 문서가 삭제됩니다")
    
    if preview['missing_collections']:
        print(f"\n❌ 존재하지 않는 컬렉션:")
        for name in preview['missing_collections']:
            print(f"  - {name}")
    
    if preview['collections']:
        print(f"\n✅ 삭제될 컬렉션:")
        for col in preview['collections']:
            print(f"  - {col['name']}: {col['document_count']}개 문서")
            if col['sources']:
                print(f"    📂 소스: {', '.join(col['sources'][:3])}")


# 대화형 삭제 함수
def interactive_delete():
    """대화형 컬렉션 삭제"""
    print("🗑️ 대화형 컬렉션 삭제")
    print("=" * 40)
    
    collections = list_collections()
    if not collections:
        print("📭 삭제할 컬렉션이 없습니다.")
        return
    
    print("현재 컬렉션:")
    for i, name in enumerate(collections, 1):
        try:
            info = get_collection_info(name)
            doc_count = info.get('count', 0)
            print(f"  {i:2d}. {name} ({doc_count}개 문서)")
        except:
            print(f"  {i:2d}. {name}")
    
    print("\n삭제 옵션:")
    print("1. 개별 컬렉션 삭제")
    print("2. 여러 컬렉션 삭제")
    print("3. 빈 컬렉션 삭제")
    print("4. 테스트 컬렉션 삭제")
    print("0. 취소")
    
    try:
        choice = input("\n선택하세요: ").strip()
        
        if choice == "0":
            print("❌ 삭제가 취소되었습니다.")
            return
        elif choice == "1":
            # 개별 삭제 로직
            print("개별 삭제는 delete_collection() 함수를 사용하세요.")
        elif choice == "2":
            # 여러 삭제 로직  
            print("여러 삭제는 delete_multiple_collections() 함수를 사용하세요.")
        elif choice == "3":
            # 빈 컬렉션 삭제
            print("빈 컬렉션 삭제를 실행합니다...")
            result = delete_empty_collections(force=True)
            print(f"결과: {result}")
        elif choice == "4":
            # 테스트 컬렉션 삭제
            print("테스트 컬렉션 삭제를 실행합니다...")
            result = delete_test_collections(force=True)
            print(f"결과: {result}")
        else:
            print("❌ 잘못된 선택입니다.")
            
    except KeyboardInterrupt:
        print("\n❌ 삭제가 취소되었습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    # 테스트 실행
    interactive_delete()