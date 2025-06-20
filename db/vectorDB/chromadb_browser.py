#!/usr/bin/env python3
"""
ChromaDB 브라우저 - 터미널 기반 ChromaDB 탐색 도구
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from db.vectorDB.chromaDB import (
    get_client,
    get_collection_info,
    list_collections,
    search_similar,
)
from db.vectorDB.chromaDB.delete import (
    delete_collection,
    delete_empty_collections,
    delete_multiple_collections,
    show_deletion_preview,
)
from db.vectorDB.chromaDB.utils import get_collection_stats, test_connection


def show_menu():
    """메인 메뉴 출력"""
    print("\n" + "=" * 40)
    print("📋 ChromaDB 브라우저 메뉴")
    print("=" * 40)
    print("1. 컬렉션 목록 보기")
    print("2. 컬렉션 상세 정보")
    print("3. 문서 검색")
    print("4. 컬렉션 내용 보기")
    print("5. ChromaDB 상태 확인")
    print("6. 컬렉션 삭제")
    print("0. 종료")
    print("=" * 40)


def show_collections():
    """컬렉션 목록 보기"""
    print("\n📂 컬렉션 목록")
    print("-" * 50)

    try:
        collections = list_collections()

        if not collections:
            print("📭 컬렉션이 없습니다.")
            return

        stats = get_collection_stats()

        print(f"총 {len(collections)}개의 컬렉션:")
        for i, collection_name in enumerate(collections, 1):
            collection_stats = stats["collections"].get(collection_name, {})
            doc_count = collection_stats.get("count", 0)
            print(f"  {i:2d}. {collection_name} ({doc_count}개 문서)")

            # 타입 분포 표시
            types = collection_stats.get("types", {})
            if types:
                type_summary = ", ".join([f"{k}:{v}" for k, v in types.items()])
                print(f"      📋 타입: {type_summary}")

        print(f"\n📊 전체 통계: {stats['total_documents']}개 문서")

    except Exception as e:
        print(f"❌ 컬렉션 목록 조회 실패: {e}")


def show_collection_detail():
    """컬렉션 상세 정보"""
    collections = list_collections()

    if not collections:
        print("📭 컬렉션이 없습니다.")
        return

    print("\n📂 컬렉션 선택")
    print("-" * 30)
    for i, collection_name in enumerate(collections, 1):
        print(f"  {i}. {collection_name}")

    try:
        choice = input("\n번호를 선택하세요 (0: 취소): ").strip()
        if choice == "0":
            return

        idx = int(choice) - 1
        if 0 <= idx < len(collections):
            collection_name = collections[idx]

            print(f"\n📋 컬렉션 '{collection_name}' 상세 정보")
            print("-" * 60)

            info = get_collection_info(collection_name)

            print(f"📄 총 문서 수: {info.get('count', 0)}개")
            print(f"🆔 샘플 ID: {', '.join(info.get('sample_ids', [])[:3])}")

            # 메타데이터 통계
            stats = info.get("stats", {})

            if stats.get("types"):
                print(f"\n📋 문서 타입 분포:")
                for doc_type, count in stats["types"].items():
                    print(f"  - {doc_type}: {count}개")

            if stats.get("sources"):
                print(f"\n📂 소스 파일 분포:")
                for source, count in stats["sources"].items():
                    print(f"  - {source}: {count}개")

        else:
            print("❌ 잘못된 번호입니다.")

    except ValueError:
        print("❌ 숫자를 입력해주세요.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def search_documents():
    """문서 검색"""
    collections = list_collections()

    if not collections:
        print("📭 컬렉션이 없습니다.")
        return

    print("\n🔍 문서 검색")
    print("-" * 30)

    # 컬렉션 선택
    for i, collection_name in enumerate(collections, 1):
        print(f"  {i}. {collection_name}")

    try:
        choice = input("\n컬렉션 번호를 선택하세요 (0: 취소): ").strip()
        if choice == "0":
            return

        idx = int(choice) - 1
        if not (0 <= idx < len(collections)):
            print("❌ 잘못된 번호입니다.")
            return

        collection_name = collections[idx]

        # 검색어 입력
        query = input(f"\n검색어를 입력하세요: ").strip()
        if not query:
            print("❌ 검색어를 입력해주세요.")
            return

        # 결과 수 입력
        try:
            n_results = input("결과 수 (기본값: 5): ").strip()
            n_results = int(n_results) if n_results else 5
        except ValueError:
            n_results = 5

        print(f"\n🔍 '{query}' 검색 결과 (컬렉션: {collection_name})")
        print("-" * 60)

        # 검색 실행
        results = search_similar(query, collection_name, n_results=n_results)

        if not results:
            print("📭 검색 결과가 없습니다.")
            return

        for i, result in enumerate(results, 1):
            similarity = result["similarity"]
            content = result["content"]
            metadata = result.get("metadata", {})

            print(f"\n[{i}] 유사도: {similarity:.3f}")
            print(f"📝 내용: {content[:100]}{'...' if len(content) > 100 else ''}")

            # 주요 메타데이터만 표시
            if metadata:
                important_keys = ["source", "chunk_type", "page", "section"]
                shown_meta = {k: v for k, v in metadata.items() if k in important_keys}
                if shown_meta:
                    meta_str = ", ".join([f"{k}:{v}" for k, v in shown_meta.items()])
                    print(f"🏷️  {meta_str}")

    except ValueError:
        print("❌ 숫자를 입력해주세요.")
    except Exception as e:
        print(f"❌ 검색 실패: {e}")


def show_collection_contents():
    """컬렉션 내용 보기"""
    collections = list_collections()

    if not collections:
        print("📭 컬렉션이 없습니다.")
        return

    print("\n📄 컬렉션 내용 보기")
    print("-" * 30)

    # 컬렉션 선택
    for i, collection_name in enumerate(collections, 1):
        print(f"  {i}. {collection_name}")

    try:
        choice = input("\n번호를 선택하세요 (0: 취소): ").strip()
        if choice == "0":
            return

        idx = int(choice) - 1
        if not (0 <= idx < len(collections)):
            print("❌ 잘못된 번호입니다.")
            return

        collection_name = collections[idx]

        # 표시할 문서 수 입력
        try:
            limit = input("표시할 문서 수 (기본값: 5): ").strip()
            limit = int(limit) if limit else 5
        except ValueError:
            limit = 5

        print(f"\n📄 컬렉션 '{collection_name}' 내용 (최대 {limit}개)")
        print("-" * 60)

        # 컬렉션 데이터 조회
        client = get_client()
        collection = client.get_client().get_or_create_collection(collection_name)
        data = collection.get(limit=limit)

        if not data["documents"]:
            print("📭 문서가 없습니다.")
            return

        for i in range(len(data["documents"])):
            doc_id = data["ids"][i]
            content = data["documents"][i]
            metadata = data["metadatas"][i] if data["metadatas"] else {}

            print(f"\n[{i+1}] ID: {doc_id}")
            print(f"📝 내용: {content[:150]}{'...' if len(content) > 150 else ''}")

            if metadata:
                # 주요 메타데이터만 표시
                important_keys = [
                    "source",
                    "chunk_type",
                    "page",
                    "section",
                    "block_index",
                ]
                shown_meta = {k: v for k, v in metadata.items() if k in important_keys}
                if shown_meta:
                    print(f"🏷️  메타데이터:")
                    for k, v in shown_meta.items():
                        print(f"    {k}: {v}")

    except ValueError:
        print("❌ 숫자를 입력해주세요.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def show_status():
    """ChromaDB 상태 확인"""
    print("\n📊 ChromaDB 상태")
    print("-" * 50)

    try:
        # 연결 상태
        client = get_client()
        connection_ok = test_connection()

        print(f"🔗 연결 상태: {'✅ 정상' if connection_ok else '❌ 실패'}")

        client_info = client.get_info()
        print(f"💾 저장소: {client_info['server_url']}")
        print(f"📁 로컬 경로: {client_info.get('local_path', 'N/A')}")
        print(f"🧮 임베딩 모델: {client_info['embedding_model']}")

        # 통계 정보
        if connection_ok:
            stats = get_collection_stats()
            print(f"\n📈 데이터 통계:")
            print(f"  총 컬렉션: {stats['total_collections']}개")
            print(f"  총 문서: {stats['total_documents']}개")

            # 컬렉션별 요약
            if stats["collections"]:
                print(f"\n📂 컬렉션별 문서 수:")
                for name, info in stats["collections"].items():
                    print(f"  - {name}: {info['count']}개")

    except Exception as e:
        print(f"❌ 상태 조회 실패: {e}")


def delete_collection_interactive():
    """컬렉션 삭제 (대화형)"""
    collections = list_collections()

    if not collections:
        print("📭 삭제할 컬렉션이 없습니다.")
        return

    print("\n🗑️ 컬렉션 삭제")
    print("-" * 50)
    print("⚠️ 주의: 삭제된 컬렉션은 복구할 수 없습니다!")
    print("-" * 50)

    print("삭제 옵션:")
    print("1. 개별 컬렉션 삭제")
    print("2. 여러 컬렉션 삭제")
    print("3. 빈 컬렉션 삭제")
    print("4. 테스트 컬렉션 삭제 (이름에 'test' 포함)")
    print("0. 취소")

    try:
        option = input("\n삭제 옵션을 선택하세요: ").strip()

        if option == "0":
            print("❌ 삭제가 취소되었습니다.")
            return
        elif option == "1":
            delete_single_collection(collections)
        elif option == "2":
            delete_multiple_collections_interactive(collections)
        elif option == "3":
            delete_empty_collections_interactive()
        elif option == "4":
            delete_test_collections_interactive()
        else:
            print("❌ 잘못된 옵션입니다.")

    except KeyboardInterrupt:
        print("\n❌ 삭제가 취소되었습니다.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def delete_single_collection(collections):
    """개별 컬렉션 삭제"""
    print("\n📋 컬렉션 목록:")
    for i, collection_name in enumerate(collections, 1):
        try:
            info = get_collection_info(collection_name)
            doc_count = info.get("count", 0)
            print(f"  {i:2d}. {collection_name} ({doc_count}개 문서)")
        except:
            print(f"  {i:2d}. {collection_name}")

    try:
        choice = input("\n삭제할 컬렉션 번호를 선택하세요 (0: 취소): ").strip()
        if choice == "0":
            return

        idx = int(choice) - 1
        if not (0 <= idx < len(collections)):
            print("❌ 잘못된 번호입니다.")
            return

        collection_name = collections[idx]

        # 삭제 미리보기
        print(f"\n📋 삭제 미리보기:")
        show_deletion_preview([collection_name])

        # 최종 확인
        confirm = input("\n삭제하려면 'DELETE'를 입력하세요: ").strip()
        if confirm != "DELETE":
            print("❌ 삭제가 취소되었습니다.")
            return

        # 삭제 실행
        print(f"\n🗑️ '{collection_name}' 삭제 중...")
        success = delete_collection(collection_name, force=True)

        if success:
            print(f"✅ 컬렉션 '{collection_name}'이 성공적으로 삭제되었습니다.")
        else:
            print(f"❌ 컬렉션 '{collection_name}' 삭제에 실패했습니다.")

    except ValueError:
        print("❌ 숫자를 입력해주세요.")


def delete_multiple_collections_interactive(collections):
    """여러 컬렉션 삭제"""
    print("\n📋 컬렉션 목록:")
    for i, collection_name in enumerate(collections, 1):
        try:
            info = get_collection_info(collection_name)
            doc_count = info.get("count", 0)
            print(f"  {i:2d}. {collection_name} ({doc_count}개 문서)")
        except:
            print(f"  {i:2d}. {collection_name}")

    try:
        indices_input = input(
            "\n삭제할 컬렉션 번호들을 쉼표로 구분해서 입력하세요 (예: 1,3,5): "
        ).strip()
        if not indices_input:
            print("❌ 입력이 없습니다.")
            return

        # 번호 파싱
        indices = []
        for idx_str in indices_input.split(","):
            try:
                idx = int(idx_str.strip()) - 1
                if 0 <= idx < len(collections):
                    indices.append(idx)
                else:
                    print(f"⚠️ 잘못된 번호 무시: {idx_str.strip()}")
            except ValueError:
                print(f"⚠️ 잘못된 형식 무시: {idx_str.strip()}")

        if not indices:
            print("❌ 유효한 번호가 없습니다.")
            return

        selected_collections = [collections[i] for i in indices]

        # 삭제 미리보기
        print(f"\n📋 삭제 미리보기:")
        show_deletion_preview(selected_collections)

        # 최종 확인
        confirm = input(
            f"\n{len(selected_collections)}개 컬렉션을 삭제하려면 'DELETE'를 입력하세요: "
        ).strip()
        if confirm != "DELETE":
            print("❌ 삭제가 취소되었습니다.")
            return

        # 삭제 실행
        print(f"\n🗑️ {len(selected_collections)}개 컬렉션 삭제 중...")
        results = delete_multiple_collections(selected_collections, force=True)

        # 결과 출력
        successful = sum(1 for success in results.values() if success)
        print(f"\n📊 삭제 결과: {successful}/{len(selected_collections)}개 성공")

        for name, success in results.items():
            status = "✅ 성공" if success else "❌ 실패"
            print(f"  - {name}: {status}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def delete_empty_collections_interactive():
    """빈 컬렉션 삭제"""
    print("\n📭 빈 컬렉션 삭제")
    print("-" * 30)

    try:
        # 빈 컬렉션 찾기
        collections = list_collections()
        empty_collections = []

        for collection_name in collections:
            try:
                info = get_collection_info(collection_name)
                if info.get("count", 0) == 0:
                    empty_collections.append(collection_name)
            except:
                continue

        if not empty_collections:
            print("📭 삭제할 빈 컬렉션이 없습니다.")
            return

        print(f"발견된 빈 컬렉션 ({len(empty_collections)}개):")
        for name in empty_collections:
            print(f"  - {name}")

        # 확인
        confirm = (
            input(f"\n{len(empty_collections)}개 빈 컬렉션을 삭제하시겠습니까? (y/N): ")
            .strip()
            .lower()
        )
        if confirm != "y":
            print("❌ 삭제가 취소되었습니다.")
            return

        # 삭제 실행
        print(f"\n🗑️ 빈 컬렉션 삭제 중...")
        results = delete_empty_collections(force=True)

        if results:
            successful = sum(1 for success in results.values() if success)
            print(f"✅ {successful}개 빈 컬렉션이 삭제되었습니다.")
        else:
            print("❌ 빈 컬렉션 삭제에 실패했습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def delete_test_collections_interactive():
    """테스트 컬렉션 삭제"""
    print("\n🧪 테스트 컬렉션 삭제")
    print("-" * 30)

    try:
        # 테스트 컬렉션 찾기
        collections = list_collections()
        test_collections = [name for name in collections if "test" in name.lower()]

        if not test_collections:
            print("🧪 삭제할 테스트 컬렉션이 없습니다.")
            return

        print(f"발견된 테스트 컬렉션 ({len(test_collections)}개):")
        for name in test_collections:
            try:
                info = get_collection_info(name)
                doc_count = info.get("count", 0)
                print(f"  - {name} ({doc_count}개 문서)")
            except:
                print(f"  - {name}")

        # 삭제 미리보기
        print(f"\n📋 삭제 미리보기:")
        show_deletion_preview(test_collections)

        # 확인
        confirm = input(
            f"\n{len(test_collections)}개 테스트 컬렉션을 삭제하려면 'DELETE'를 입력하세요: "
        ).strip()
        if confirm != "DELETE":
            print("❌ 삭제가 취소되었습니다.")
            return

        # 삭제 실행
        print(f"\n🗑️ 테스트 컬렉션 삭제 중...")
        from db.vectorDB.chromaDB.delete import delete_test_collections

        results = delete_test_collections(force=True)

        if results:
            successful = sum(1 for success in results.values() if success)
            print(f"✅ {successful}개 테스트 컬렉션이 삭제되었습니다.")

            for name, success in results.items():
                status = "✅ 성공" if success else "❌ 실패"
                print(f"  - {name}: {status}")
        else:
            print("❌ 테스트 컬렉션 삭제에 실패했습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")


def main():
    """메인 실행 함수"""
    print("🎯 ChromaDB 브라우저 시작")

    # 초기 연결 확인
    try:
        client = get_client()
        if not test_connection():
            print("❌ ChromaDB 연결에 실패했습니다.")
            return

        print(f"✅ ChromaDB 연결 성공 ({client.get_info()['server_url']})")

    except Exception as e:
        print(f"❌ ChromaDB 초기화 실패: {e}")
        return

    # 메인 루프
    while True:
        try:
            show_menu()
            choice = input("\n선택하세요: ").strip()

            if choice == "0":
                print("\n👋 ChromaDB 브라우저를 종료합니다.")
                break
            elif choice == "1":
                show_collections()
            elif choice == "2":
                show_collection_detail()
            elif choice == "3":
                search_documents()
            elif choice == "4":
                show_collection_contents()
            elif choice == "5":
                show_status()
            elif choice == "6":
                delete_collection_interactive()
            else:
                print("❌ 잘못된 선택입니다. 0-6 사이의 숫자를 입력해주세요.")

            # 계속하기
            if choice != "0":
                input("\n⏎ 계속하려면 Enter를 누르세요...")

        except KeyboardInterrupt:
            print("\n\n👋 ChromaDB 브라우저를 종료합니다.")
            break
        except Exception as e:
            print(f"\n❌ 예상치 못한 오류: {e}")
            input("⏎ 계속하려면 Enter를 누르세요...")


if __name__ == "__main__":
    main()
