```bash
tests/
├── conftest.py                    # 전체 프로젝트 공통 fixtures
├── tests/                                 # 🧪 테스트
│   ├── __init__.py
│   ├── conftest.py                        # Pytest 설정
│   ├── unit/                              # 단위 테스트
│   │   ├── agents/                        # Agent별 테스트
│   │   │   ├── document_analyzer/          # DocumentAnalyzer Agent
│   │   │   │   ├── tools/                     # Agent 도구 테스트
│   │   │   │   │   ├── test_text_analyzer.py
│   │   │   │   │   ├── test_structure_parser.py
│   │   │   │   │   ├── test_difficulty_assessor.py
│   │   │   │   │   └── test_keyword_extractor.py
│   │   │   │   └── test_document_analyzer.py
│   │   │   ├── question_generator/          # QuestionGenerator Agent
│   │   │   │   ├── tools/                     # Agent 도구 테스트
│   │   │   │   │   ├── test_question_generator.py
│   │   │   │   └── test_answer_generator.py
│   │   │   ├── grader/                        # Grader Agent
│   │   │   │   ├── tools/                     # Agent 도구 테스트
│   │   │   │   │   ├── test_answer_grader.py
│   │   │   │   └── test_feedback_generator.py
│   │   │   └── assistant/                     # Assistant Agent
│   │   │       ├── tools/                     # Agent 도구 테스트
│   │   │       └── test_assistant.py
│   │   ├── pipelines/                     # Pipeline별 테스트
│   │   │   ├── test_document_processing.py
│   │   │   ├── test_test_generation.py
│   │   │   ├── test_grading.py
│   │   │   └── test_assistant_pipeline.py
│   │   └── shared/                        # 공유 컴포넌트 테스트
│   │       ├── test_database.py
│   │       ├── test_models.py
│   │       └── test_utils.py
│   ├── integration/                       # 통합 테스트
│   │   ├── test_agent_collaboration.py    # Agent 간 협업 테스트
│   │   ├── test_pipeline_workflows.py     # Pipeline 워크플로우 테스트
│   │   └── test_api_integration.py        # API 통합 테스트
│   ├── performance/                       # 성능 테스트
│   │   ├── test_load_testing.py
│   │   ├── test_memory_usage.py
│   │   └── test_response_times.py
│   ├── e2e/                          # End-to-End 테스트
│   │   ├── conftest.py
│   │   ├── test_complete_flow.py
│   │   └── test_user_scenarios.py
│   └── fixtures/                          # 테스트 데이터
│       ├── __init__.py
│       ├── sample_documents/
│       ├── sample_questions/
│       └── mock_responses/
```