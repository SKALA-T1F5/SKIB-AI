# ChromaDB 벡터 데이터베이스 모듈

이 모듈은 ChromaDB를 사용한 벡터 저장, 검색, 관리 기능을 제공합니다.

## 📁 구조

```
chromaDB/
├── __init__.py           # 모듈 초기화 및 주요 함수 export
├── config.py            # 설정 관리 (원격/로컬, 인증 등)
├── client.py            # ChromaDB 클라이언트 연결 및 관리
├── upload.py            # 문서 업로드 및 임베딩 생성
├── search.py            # 벡터 검색 및 유사도 검색
├── utils.py             # 유틸리티 함수들
├── pipeline.py          # 통합 워크플로우 파이프라인
├── examples.py          # 사용 예제
└── README.md           # 이 파일
```

## 🚀 빠른 시작

### 1. 기본 설정

`.env.chromadb` 파일을 프로젝트 루트에 생성:

```bash
# ChromaDB 서버 설정
CHROMADB_URL=https://chromadb-1.skala25a.project.skala-ai.com
CHROMADB_USERNAME=skala
CHROMADB_PASSWORD=Skala25a!23$

# 로컬 개발용 설정
LOCAL_CHROMADB_PATH=chroma_data

# 기타 설정
USE_REMOTE_CHROMADB=true
EMBEDDING_MODEL=BAAI/bge-base-en
```

### 2. 기본 사용법

```python
from db.vectorDB.chromaDB import (
    get_client, upload_documents, search_similar, 
    list_collections, get_collection_info
)

# 연결 테스트
client = get_client()
client.test_connection()

# 문서 업로드
document_blocks = [
    {
        "content": "ChromaDB는 벡터 데이터베이스입니다.",
        "type": "text",
        "metadata": {"page": 1, "section": "intro"}
    }
]

uploaded_count = upload_documents(
    document_blocks, 
    "my_collection", 
    "example.txt"
)

# 검색
results = search_similar("벡터 검색", "my_collection", n_results=5)
for result in results:
    print(f"유사도: {result['similarity']:.3f}")
    print(f"내용: {result['content']}")
```

### 3. 파이프라인 사용

```python
from db.vectorDB.chromaDB.pipeline import ChromaDBPipeline

pipeline = ChromaDBPipeline()

# 문서 처리 및 업로드
result = pipeline.process_and_upload_document(
    document_blocks, 
    "my_collection", 
    "document.pdf"
)

# 검색 및 분석
search_result = pipeline.search_and_analyze(
    "검색어", 
    "my_collection", 
    n_results=5
)
```

## 🔧 주요 기능

### 클라이언트 관리
- 원격/로컬 ChromaDB 자동 연결
- 연결 실패 시 자동 fallback
- 연결 상태 모니터링

### 문서 업로드
- 단일/배치 업로드 지원
- 자동 임베딩 생성 (BAAI/bge-base-en)
- 메타데이터 처리 및 정리
- 업로드 통계 및 오류 처리

### 벡터 검색
- 유사도 검색 (코사인 유사도)
- 메타데이터 기반 필터링
- 하이브리드 검색 (벡터 + 메타데이터)
- 검색 결과 분석

### 컬렉션 관리
- 컬렉션 생성/삭제/조회
- 컬렉션 정보 및 통계
- 전체 데이터베이스 상태 모니터링

## 📊 데이터 구조

### 문서 블록 형식
```python
document_block = {
    "content": "텍스트 내용",
    "type": "text|table|heading|image",
    "metadata": {
        "page": 1,
        "section": "intro",
        "source_file": "document.pdf",
        # 기타 메타데이터...
    }
}
```

### 검색 결과 형식
```python
search_result = {
    "content": "문서 내용",
    "metadata": {...},
    "similarity": 0.85,
    "distance": 0.15,
    "id": "chunk_id"
}
```

## 🔍 검색 옵션

### 기본 벡터 검색
```python
results = search_similar(
    query="검색어",
    collection_name="my_collection",
    n_results=5,
    where={"chunk_type": "text"}  # 메타데이터 필터
)
```

### 메타데이터 검색
```python
from db.vectorDB.chromaDB.search import ChromaDBSearcher

searcher = ChromaDBSearcher()

# 타입별 검색
results = searcher.search_by_type("my_collection", "heading")

# 소스별 검색
results = searcher.search_by_source("my_collection", "document.pdf")

# 하이브리드 검색
results = searcher.hybrid_search(
    query="검색어",
    collection_name="my_collection",
    metadata_filter={"page": 1},
    min_similarity=0.7
)
```

## 🔧 설정 옵션

### ChromaDBConfig 클래스
```python
from db.vectorDB.chromaDB.config import get_config

config = get_config()
print(config.remote_url)        # 원격 서버 URL
print(config.use_remote)        # 원격 사용 여부
print(config.local_path)        # 로컬 저장 경로
print(config.embedding_model)   # 임베딩 모델
```

## 🚨 오류 처리

### 연결 실패 처리
- 원격 연결 실패 시 자동으로 로컬 ChromaDB 사용
- 연결 상태 실시간 모니터링
- 재연결 시도 및 fallback 메커니즘

### 업로드 오류 처리
- 배치 업로드 시 개별 실패 처리
- 메타데이터 타입 자동 변환
- 업로드 통계 및 실패 로그

## 📈 성능 최적화

### 배치 처리
- 기본 배치 크기: 50개
- 메모리 효율적인 청크 처리
- 임베딩 생성 최적화

### 검색 최적화
- 코사인 유사도 인덱스 사용
- 메타데이터 필터링으로 검색 범위 제한
- 결과 캐싱 (필요시 구현 가능)

## 🔗 DocumentAnalyzer 통합

```python
from src.agents.document_analyzer.agent import DocumentAnalyzerAgent

# 자동 ChromaDB 업로드 활성화
analyzer = DocumentAnalyzerAgent(
    collection_name="my_docs",
    auto_upload_chromadb=True
)

result = analyzer.analyze_document("document.pdf")
print(f"ChromaDB 업로드: {result.get('chromadb_uploaded')}")
print(f"업로드된 청크: {result.get('chromadb_upload_count')}")
```

## 🛠️ 디버깅 및 모니터링

### 상태 확인
```python
from db.vectorDB.chromaDB.utils import get_collection_stats, test_connection

# 연결 테스트
test_connection()

# 전체 통계
stats = get_collection_stats()
print(f"컬렉션 수: {stats['total_collections']}")
print(f"총 문서: {stats['total_documents']}")
```

### 로깅
```python
import logging
logging.basicConfig(level=logging.INFO)

# ChromaDB 관련 로그가 출력됩니다
```

## 📝 예제 실행

```bash
# 모든 예제 실행
python db/vectorDB/chromaDB/examples.py

# 개별 예제 실행 (Python에서)
from db.vectorDB.chromaDB.examples import example_basic_usage
example_basic_usage()
```

## 🔧 문제 해결

### 일반적인 문제

1. **원격 연결 실패**
   - 인증 정보 확인
   - 네트워크 연결 상태 확인
   - 로컬 fallback 사용

2. **임베딩 모델 로딩 실패**
   - `sentence-transformers` 설치 확인
   - 모델 다운로드 대기

3. **메타데이터 오류**
   - ChromaDB는 string, int, float, bool만 지원
   - 자동 변환 기능 사용

### 로그 확인
```python
import logging
logging.getLogger('db.vectorDB.chromaDB').setLevel(logging.DEBUG)
```

이 모듈을 통해 ChromaDB의 모든 기능을 편리하게 사용할 수 있습니다!