"""
Test Generation Pipeline 전용 Redis 세션 관리자
- LangGraph State는 워크플로우 제어용 메타데이터만 관리
- Redis는 대용량 데이터 저장 담당 (생성된 문제, 상세 결과)
- 필수적인 함수들만 포함
"""

import json
from typing import Any, Dict, List, Optional

from db.redisDB.redis_client import redis_client

# ============ 핵심 Redis 키 생성기 ============


def get_batch_questions_key(pipeline_id: str, batch_id: int) -> str:
    """배치별 생성된 문제 Redis 키"""
    return f"testgen:questions:{pipeline_id}:{batch_id}"


def get_final_test_key(pipeline_id: str) -> str:
    """최종 테스트 결과 Redis 키"""
    return f"testgen:final_test:{pipeline_id}"


def get_batch_summary_key(pipeline_id: str, batch_id: int) -> str:
    """배치 요약 정보 Redis 키 (LangGraph 조건부 분기용)"""
    return f"testgen:batch_summary:{pipeline_id}:{batch_id}"


# ============ 핵심 데이터 관리 함수 ============


async def save_batch_questions(
    pipeline_id: str, batch_id: int, questions: List[Dict[str, Any]]
) -> bool:
    """
    배치별 생성된 문제들을 Redis에 저장 (대용량 데이터)

    Args:
        pipeline_id: Pipeline 고유 ID
        batch_id: 배치 ID
        questions: 생성된 문제 목록

    예시 questions:
    [
        {
            "id": "q_001",
            "type": "objective",
            "question": "다음 중 마이크로서비스의 특징은?",
            "options": ["A) 단일 배포", "B) 서비스별 독립 배포", "C) 공유 데이터베이스"],
            "answer": "B",
            "document_id": 101,
            "keywords": ["마이크로서비스", "배포"],
            "quality_score": 0.85
        }
    ]
    """
    try:
        key = get_batch_questions_key(pipeline_id, batch_id)
        await redis_client.set(key, json.dumps(questions), ex=7200)  # 2시간 TTL
        return True
    except Exception as e:
        print(f"❌ 배치 문제 저장 실패 ({pipeline_id}, batch {batch_id}): {e}")
        return False


async def load_batch_questions(pipeline_id: str, batch_id: int) -> List[Dict[str, Any]]:
    """배치별 생성된 문제들을 Redis에서 로드"""
    try:
        key = get_batch_questions_key(pipeline_id, batch_id)
        raw = await redis_client.get(key)
        return json.loads(raw) if raw else []
    except Exception as e:
        print(f"❌ 배치 문제 로드 실패 ({pipeline_id}, batch {batch_id}): {e}")
        return []


async def save_batch_summary(
    pipeline_id: str, batch_id: int, summary: Dict[str, Any]
) -> bool:
    """
    배치 처리 요약 정보 저장 (LangGraph 조건부 분기용)

    예시 summary:
    {
        "batch_id": 1,
        "status": "completed",
        "questions_generated": 5,
        "average_quality": 0.86,
        "processing_time": 120,
        "retry_count": 1,
        "search_contexts_count": 12,
        "keywords_covered": ["시스템", "아키텍처"]
    }
    """
    try:
        key = get_batch_summary_key(pipeline_id, batch_id)
        await redis_client.set(key, json.dumps(summary), ex=3600)  # 1시간 TTL
        return True
    except Exception as e:
        print(f"❌ 배치 요약 저장 실패 ({pipeline_id}, batch {batch_id}): {e}")
        return False


async def load_batch_summary(
    pipeline_id: str, batch_id: int
) -> Optional[Dict[str, Any]]:
    """배치 처리 요약 정보 로드"""
    try:
        key = get_batch_summary_key(pipeline_id, batch_id)
        raw = await redis_client.get(key)
        return json.loads(raw) if raw else None
    except Exception as e:
        print(f"❌ 배치 요약 로드 실패 ({pipeline_id}, batch {batch_id}): {e}")
        return None


async def save_final_test(pipeline_id: str, test_data: Dict[str, Any]) -> bool:
    """
    최종 테스트 결과 저장

    예시 test_data:
    {
        "total_questions": 15,
        "questions": [...],  # 모든 배치의 문제들 통합
        "metadata": {
            "total_processing_time": 342,
            "average_quality_score": 0.84,
            "questions_by_type": {"objective": 10, "subjective": 5},
            "questions_by_document": {"doc_101": 6, "doc_102": 4, "doc_103": 5},
            "keywords_coverage": ["시스템 아키텍처", "데이터베이스", "보안"],
            "successful_batches": 3,
            "failed_batches": 0
        }
    }
    """
    try:
        key = get_final_test_key(pipeline_id)
        await redis_client.set(key, json.dumps(test_data), ex=86400)  # 24시간 TTL
        return True
    except Exception as e:
        print(f"❌ 최종 테스트 저장 실패 ({pipeline_id}): {e}")
        return False


async def load_final_test(pipeline_id: str) -> Optional[Dict[str, Any]]:
    """최종 테스트 결과 로드"""
    try:
        key = get_final_test_key(pipeline_id)
        raw = await redis_client.get(key)
        return json.loads(raw) if raw else None
    except Exception as e:
        print(f"❌ 최종 테스트 로드 실패 ({pipeline_id}): {e}")
        return None


# ============ 배치별 컨텍스트 저장 (검색 결과) ============


def get_batch_contexts_key(pipeline_id: str, batch_id: int) -> str:
    """배치별 VectorDB 검색 컨텍스트 Redis 키"""
    return f"testgen:contexts:{pipeline_id}:{batch_id}"


async def save_batch_contexts(
    pipeline_id: str, batch_id: int, contexts: List[Dict[str, Any]]
) -> bool:
    """
    배치별 VectorDB 검색 컨텍스트 저장

    예시 contexts:
    [
        {
            "content": "마이크로서비스는 독립적으로 배포 가능한 서비스들로 구성...",
            "metadata": {"page": 5, "source": "system_design.pdf"},
            "similarity": 0.89,
            "search_keyword": "마이크로서비스"
        }
    ]
    """
    try:
        key = get_batch_contexts_key(pipeline_id, batch_id)
        await redis_client.set(key, json.dumps(contexts), ex=3600)  # 1시간 TTL
        return True
    except Exception as e:
        print(f"❌ 배치 컨텍스트 저장 실패 ({pipeline_id}, batch {batch_id}): {e}")
        return False


async def load_batch_contexts(pipeline_id: str, batch_id: int) -> List[Dict[str, Any]]:
    """배치별 VectorDB 검색 컨텍스트 로드"""
    try:
        key = get_batch_contexts_key(pipeline_id, batch_id)
        raw = await redis_client.get(key)
        return json.loads(raw) if raw else []
    except Exception as e:
        print(f"❌ 배치 컨텍스트 로드 실패 ({pipeline_id}, batch {batch_id}): {e}")
        return []


# ============ 정리 함수 ============


async def cleanup_pipeline_data(pipeline_id: str) -> bool:
    """Pipeline 완료 후 Redis 데이터 정리"""
    try:
        # 삭제할 키 패턴들
        patterns = [
            f"testgen:questions:{pipeline_id}:*",
            f"testgen:batch_summary:{pipeline_id}:*",
            f"testgen:contexts:{pipeline_id}:*",
            f"testgen:final_test:{pipeline_id}",
        ]

        keys_to_delete = []
        for pattern in patterns:
            if "*" in pattern:
                keys_to_delete.extend(await redis_client.keys(pattern))
            else:
                keys_to_delete.append(pattern)

        if keys_to_delete:
            await redis_client.delete(*keys_to_delete)

        print(f"✅ Pipeline Redis 데이터 정리 완료: {pipeline_id}")
        return True
    except Exception as e:
        print(f"❌ Pipeline Redis 데이터 정리 실패 ({pipeline_id}): {e}")
        return False


# ============ 편의 함수 ============


async def get_pipeline_question_count(pipeline_id: str) -> int:
    """Pipeline에서 생성된 총 문제 수 반환"""
    try:
        pattern = f"testgen:questions:{pipeline_id}:*"
        keys = await redis_client.keys(pattern)

        total_count = 0
        for key in keys:
            raw = await redis_client.get(key)
            if raw:
                questions = json.loads(raw)
                total_count += len(questions)

        return total_count
    except Exception as e:
        print(f"❌ Pipeline 문제 수 조회 실패 ({pipeline_id}): {e}")
        return 0


async def get_pipeline_completion_status(pipeline_id: str) -> Dict[str, Any]:
    """
    Pipeline 완료 상태 요약 반환

    Returns:
        {
            "total_questions": 15,
            "completed_batches": [1, 2, 3],
            "average_quality": 0.84,
            "has_final_test": True
        }
    """
    try:
        # 배치 요약 키들 조회
        pattern = f"testgen:batch_summary:{pipeline_id}:*"
        batch_keys = await redis_client.keys(pattern)

        completed_batches = []
        quality_scores = []

        for key in batch_keys:
            raw = await redis_client.get(key)
            if raw:
                summary = json.loads(raw)
                if summary.get("status") == "completed":
                    batch_id = int(key.split(":")[-1])
                    completed_batches.append(batch_id)

                    if "average_quality" in summary:
                        quality_scores.append(summary["average_quality"])

        # 최종 테스트 존재 여부
        final_test_key = get_final_test_key(pipeline_id)
        has_final_test = await redis_client.exists(final_test_key) > 0

        # 총 문제 수
        total_questions = await get_pipeline_question_count(pipeline_id)

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

        return {
            "total_questions": total_questions,
            "completed_batches": sorted(completed_batches),
            "average_quality": round(avg_quality, 2),
            "has_final_test": has_final_test,
            "completed_batch_count": len(completed_batches),
        }

    except Exception as e:
        print(f"❌ Pipeline 완료 상태 조회 실패 ({pipeline_id}): {e}")
        return {
            "total_questions": 0,
            "completed_batches": [],
            "average_quality": 0.0,
            "has_final_test": False,
            "completed_batch_count": 0,
        }
