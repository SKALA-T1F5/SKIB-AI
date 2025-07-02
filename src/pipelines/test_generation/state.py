"""
Test Generation Pipeline State - LangGraph 워크플로우 제어 전용
- 의사결정 및 조건부 분기에 필요한 최소한의 메타데이터만 포함
- 대용량 데이터(생성된 문제, 상세 로그 등)는 Redis로 분리
- 각 단계별 예시 출력을 주석으로 포함
"""

from typing import Any, Dict, List, Optional

from src.pipelines.base.state import BasePipelineState


class TestGenerationState(BasePipelineState, total=False):
    """테스트 생성 Pipeline 상태 - 워크플로우 제어용"""

    # ============ 기본 설정 정보 ============
    test_config: Dict[str, Any]
    # 예시: {
    #     "num_objective": 10,
    #     "num_subjective": 5,
    #     "difficulty_level": "medium",
    #     "total_questions": 15,
    #     "keywords": ["시스템 아키텍처", "데이터베이스"]
    # }

    documentIds: List[int]
    # 예시: [101, 102, 103]

    # ============ 테스트 계획 정보 (SubGraph 간 데이터 전달용) ============
    total_test_plan: Optional[Dict[str, Any]]
    # 예시: {
    #     "test_summary": "시스템 운영 능력 평가 테스트",
    #     "evaluation_criteria": ["기술 이해도", "문제 해결 능력"],
    #     "total_objective": 10,
    #     "total_subjective": 5,
    #     "estimated_duration": 60
    # }

    document_test_plan: Optional[Dict[str, Any]]
    # 예시: {
    #     "document_plans": [
    #         {
    #             "document_id": 101,
    #             "document_name": "system_architecture.pdf",
    #             "keywords": ["마이크로서비스", "API Gateway", "로드밸런서"],
    #             "recommended_questions": {"objective": 4, "subjective": 2},
    #             "difficulty_level": "medium",
    #             "priority": "high"
    #         }
    #     ]
    # }

    # ============ 배치 처리 메타데이터 (워크플로우 제어용) ============
    processing_batches: List[Dict[str, Any]]
    # 예시: [
    #     {
    #         "batch_id": 1,
    #         "document_ids": [101, 102],
    #         "keywords": ["시스템", "아키텍처", "설계"],
    #         "target_questions": {"objective": 6, "subjective": 3},
    #         "priority": "high"
    #     },
    #     {
    #         "batch_id": 2,
    #         "document_ids": [103],
    #         "keywords": ["데이터베이스", "트랜잭션"],
    #         "target_questions": {"objective": 4, "subjective": 2},
    #         "priority": "medium"
    #     }
    # ]

    batch_processing_strategy: str
    # 예시: "parallel" | "sequential" | "hybrid"

    # ============ 조건부 분기를 위한 상태 정보 ============
    batch_quality_scores: Dict[int, float]
    # 예시: {1: 0.85, 2: 0.89, 3: 0.72}
    # 용도: _route_after_review()에서 품질 기반 분기 결정

    regeneration_attempts: Dict[int, int]
    # 예시: {1: 0, 2: 1, 3: 2}  # 배치별 재생성 시도 횟수
    # 용도: 최대 재시도 횟수 초과 시 실패 처리 분기

    # ============ 진행 상황 추적 (워크플로우 제어용) ============
    total_batches: int
    # 예시: 3

    completed_batches: int
    # 예시: 2

    current_batch_processing: List[int]
    # 예시: [2, 3]  # 현재 처리 중인 배치 ID들

    # ============ 시스템 상태 (동적 배치 크기 조정용) ============
    system_load_metrics: Dict[str, Any]
    # 예시: {
    #     "celery_active_tasks": 4,
    #     "avg_task_completion_time": 45.2,
    #     "last_updated": "2025-01-01T10:30:00Z"
    # }
    # 용도: 시스템 부하에 따른 배치 크기 동적 조정
