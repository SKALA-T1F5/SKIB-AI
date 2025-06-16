# 🧠 SKIB-AI

AI 기반 시스템 매뉴얼/아키텍처 문서로부터 문항을 생성하고 피드백을 제공하는 지식 이전 플랫폼입니다.  

- Python 3.10
- Conda
- MongoDB
- Weaviate (Vector DB)
- FastAPI
- Docker

---

## 📁 1. 프로젝트 구조

```bash
SKIB-ai/
├── main.py                    # FastAPI entrypoint
├── agents/                    # AI Agent Development
│   ├── question_generator/
│   ├── translator/
│   ├── subgective_grader/
│   └── trainee_assistant/
│
├── api/                        
│   ├── question/
│   │   ├── routers/             # API route registration (calls agent logic)
│   │   ├── crud/                 # DB access
│   │   ├── models/               # MongoDB schemas or ORM models
│   │   └── schemas/              # Pydantic schemas for I/O
│   │
│   ├── translator/
│   │   ├── routers/
│   │   ├── crud/
│   │   ├── models/
│   │   └── schemas/
│   │
│   ├── grading/
│   │   ├── routers/
│   │   ├── crud/
│   │   ├── models/
│   │   └── schemas/
│   │
│   └── trainee_assistant/
│       ├── routers/
│       ├── crud/
│       ├── models/
│       └── schemas/
│
├── db/                           # Shared MongoDB connection logic
│   ├── client.py
│   └── init.py
│   └── vector/                   # Vector database(Weaviate) connection logic
│       ├── client.py
│       └── init.py
│
├── config/                       # App/env configs
│   ├── settings.py
│   └── .env
│
├── docker/                       # Docker/Compose files
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── services/
│   └── indexing/                 ← Docling → Chunking → Embedding → Save
│       ├── parser.py
│       ├── chunker.py
│       ├── embedder.py
│
├── tests/                        # Unit tests organized by agent
│   ├── question_generator/
│   ├── translator/
│   ├── grader/
│   └── trainee_assistant/
│
├── utils/                        # Shared utility functions
│   ├── file_parser.py
│   ├── chunker.py
│   └── logger.py
│
├── requirements.txt
├── envoronment.yml               # Conda environment file
└── README.md
```

---

## ⚙️ 2. 환경 구성


### 사전 요구 사항

- Python 3.10 설치
  - **Mac (Homebrew):** `brew install python@3.10`
  - **Windows:** [Python 3.10 다운로드](https://www.python.org/downloads/release/python-3100/)  
    설치 시 `"Add Python to PATH"` 옵션을 반드시 체크하세요.

---

### 🐍 Conda 기반 가상환경

```bash
conda env create -f environment.yml
conda activate skib
```

추가 설치 시 다음 명령어로 `environment.yml` 파일을 업데이트하세요:

```bash
conda env export --no-builds | grep -v "prefix" > environment.yml
```

#### `.env` 예시 (직접 생성 필요)

```env
MONGO_URL=mongodb://localhost:27017
```
---
### 🖥️ Mac / Linux

#### 1. 가상환경 생성 (Python 3.10 기준)

```bash
/opt/homebrew/opt/python@3.10/libexec/bin/python -m venv .venv
```

#### 2. 가상환경 활성화

```bash
source .venv/bin/activate
```

#### 3. `uv` 설치 및 의존성 설치

```bash
pip install uv
uv pip install -r requirements.txt
```

---

### 🪟 Windows

#### 1. 가상환경 생성

```powershell
python -m venv .venv
```

#### 2. 가상환경 활성화

```powershell
.venv\Scripts\activate
```

#### 3. `uv` 설치 및 의존성 설치

```powershell
pip install uv
uv pip install -r requirements.txt
```
---

## 🚀 3. 실행 방법

```bash
uvicorn main:app --reload
```

---

## 🧭 4. GitHub Projects 기반 Sprint 관리

### 🗂 Board Structure

* **Backlog**: 논의 중이거나 아이디어 단계
* **To Do**: 이번 주 스프린트 대상
* **In Progress**: 작업 진행 중
* **Blocked**: 이슈 또는 의존성으로 막힘
* **Done**: 완료

### 🧩 Task 예시

| Agent      | Task                                      | Sprint Week | Type  |
| ---------- | ----------------------------------------- | ----------- | ----- |
| QG Agent   | `extract_text_from_pdf()` 구현 (service.py) | Week 1      | Issue |
| Translator | Google Translate API 연동                   | Week 1      | Issue |
| Grading    | 채점 기준 및 포맷 설정 (rubric/)                   | Week 2      | Issue |
| Assistant  | Weaviate 기반 Retriever+Chat 구축             | Week 2      | Issue |
| Global     | FastAPI 실행용 Dockerfile + main.py 작성       | Week 1      | Issue |

---

## 📝 5. 이슈 및 PR 템플릿

### 📌 Issue Template

```md
### 🧠 기능 요약
문서 기반 LangChain QA 생성 기능 구현

### 📂 관련 파일
- `api/question/routers/`
- `api/question/services/`

### ✅ 작업 항목
- [ ] 프롬프트 설계
- [ ] LangChain 파이프라인 연동
- [ ] 응답 구조 설계
```

### ✅ PR Template

```md
### 🚀 What's in this PR?
- LangChain 기반 문항 생성 구현
- PDF 입력과 RAG 구조 연동

### 🔗 Related Issue
Fixes #12

### 📁 Affected Files
- api/question/services/service.py
- shared/utils.py
```

---

## 📎 6. 프로젝트 구성 규칙

* **모든 기능은 Issue 생성 후 진행**
* **각 기능은 Pull Request로 구현 및 Review**
* **모든 Issue는 GitHub Project와 Sprint Week에 연결**
* **에이전트당 API/서비스/모델 등 폴더 통일 구성**

---
