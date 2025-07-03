import logging

from api.question.schemas.question import (
    DifficultyLevel,
    GenerationType,
    GradingCriterion,
    QuestionResponse,
    QuestionType,
)
from api.test.schemas.test_generation_status import (
    TestGenerationStatus,
)
from api.websocket.services.springboot_notifier import (
    notify_test_generation_progress,
    notify_test_generation_result,
)
from src.agents.question_generator.agent import QuestionGeneratorAgent

logger = logging.getLogger(__name__)


async def test_generation_background(
    task_id: str, test_id: int, request_data: dict
) -> dict:
    """
    테스트 생성 백그라운드 처리 로직 (기존 generate_test_questions 로직을 업그레이드)
    """
    try:
        logger.info(f"🚀 테스트 생성 시작: test_id={test_id}, task_id={task_id}")

        # 1. 테스트 설계안 로드
        await notify_test_generation_progress(
            task_id, test_id, TestGenerationStatus.LOADING_TEST_PLAN
        )

        # 2. 테스트 계획 반영
        await notify_test_generation_progress(
            task_id, test_id, TestGenerationStatus.REFLECTING_TEST_PLAN
        )

        # 기존 로직 시작: QuestionGeneratorAgent 초기화 및 데이터 변환

        agent = QuestionGeneratorAgent()

        # 문서별 설정을 document_test_plan_data 형태로 변환
        document_plans = []
        for doc_config in request_data["document_configs"]:
            document_plan = {
                "document_name": doc_config["document_name"],
                "document_id": doc_config["documentId"],
                "keywords": doc_config["keywords"],
                "recommended_questions": {
                    "objective": doc_config["configured_objective_count"],
                    "subjective": doc_config["configured_subjective_count"],
                },
            }
            document_plans.append(document_plan)

        # 3. 문맥 검색
        await notify_test_generation_progress(
            task_id, test_id, TestGenerationStatus.RETRIEVING_CONTEXTS
        )

        # test_plan 데이터 구성
        total_test_plan_data = {
            "test_summary": request_data["summary"],
            "difficulty": request_data["difficulty_level"].lower(),
            "total_objective": sum(
                doc["configured_objective_count"]
                for doc in request_data["document_configs"]
            ),
            "total_subjective": sum(
                doc["configured_subjective_count"]
                for doc in request_data["document_configs"]
            ),
        }

        document_test_plan_data = {"document_plans": document_plans}

        # 4. 문맥 전처리
        await notify_test_generation_progress(
            task_id, test_id, TestGenerationStatus.PREPROCESSING_CONTEXTS
        )

        # 5. 문제 생성 (기존 Agent 호출)
        await notify_test_generation_progress(
            task_id, test_id, TestGenerationStatus.GENERATING_QUESTIONS
        )

        result = agent.generate_enhanced_questions_from_test_plans(
            total_test_plan_data=total_test_plan_data,
            document_test_plan_data=document_test_plan_data,
        )

        if result.get("status") == "failed":
            raise Exception(result.get("error", "문제 생성 실패"))

        # 6. 문제 후처리
        await notify_test_generation_progress(
            task_id, test_id, TestGenerationStatus.POSTPROCESSING_QUESTIONS
        )

        # 생성된 문제를 QuestionResponse 형태로 변환 (기존 로직)
        questions = []
        generated_questions = result.get("questions", [])

        for q in generated_questions:
            question_type = QuestionType(q.get("type"))

            # 난이도 매핑
            difficulty_map = {
                "easy": DifficultyLevel.easy,
                "medium": DifficultyLevel.normal,
                "hard": DifficultyLevel.hard,
            }
            difficulty = difficulty_map.get(
                q.get("difficulty", "medium"), DifficultyLevel.normal
            )

            valid_criteria_fields = {"score", "criteria", "example", "note"}
            raw_criteria = q.get("grading_criteria", [])

            grading_criteria = [
                GradingCriterion(
                    **{k: v for k, v in criterion.items() if k in valid_criteria_fields}
                )
                for criterion in raw_criteria
                if isinstance(criterion, dict)
            ]

            question_response = QuestionResponse(
                type=question_type,
                generationType=GenerationType(q.get("generation_type").upper()),
                difficulty_level=difficulty,
                question=q.get("question", ""),
                options=(
                    q.get("options")
                    if question_type == QuestionType.objective
                    else None
                ),
                answer=q.get("answer", ""),
                explanation=q.get("explanation"),
                grading_criteria=(
                    grading_criteria
                    if question_type == QuestionType.subjective
                    else None
                ),
                documentId=q.get("document_id", 0),
                document_name=q.get("document_name", ""),
                keywords=q.get("source_keywords", []),
                tags=q.get("tags", []),
            )
            questions.append(question_response)

        # 7. 결과 최종화
        await notify_test_generation_progress(
            task_id, test_id, TestGenerationStatus.FINALIZING_RESULTS
        )

        # 최종 결과 데이터 구성
        final_result = {
            "test_id": test_id,
            "questions": [
                q.model_dump(by_alias=True, exclude_none=False) for q in questions
            ],
            "total_questions": len(questions),
            "metadata": {
                "name": request_data["name"],
                "summary": request_data["summary"],
                "difficulty_level": request_data["difficulty_level"],
                "limited_time": request_data["limited_time"],
                "pass_score": request_data["pass_score"],
                "is_retake": request_data["is_retake"],
            },
        }

        logger.info(f"🧪 Test ID: {final_result.get('test_id')}")
        logger.info(f"📊 Total Questions: {final_result.get('total_questions')}")
        logger.info(f"📝 Metadata: {final_result.get('metadata')}")

        await notify_test_generation_result(
            task_id=task_id, test_id=test_id, result_data=final_result
        )

        # 8. 완료
        await notify_test_generation_progress(
            task_id, test_id, TestGenerationStatus.COMPLETED
        )

        logger.info(f"✅ 테스트 생성 완료: test_id={test_id}")

        return {"status": "success", "test_id": test_id, "questions": questions}

    except Exception as e:
        logger.error(f"❌ 테스트 생성 실패: test_id={test_id}, error={str(e)}")

        # 실패 알림
        from api.websocket.schemas.task_progress import TaskStatus
        from api.websocket.services.progress_tracker import save_task_progress

        await save_task_progress(
            task_id=task_id,
            status=TaskStatus.FAILED,
            progress=0.0,
            message=f"테스트 생성 실패: {str(e)}",
        )

        raise e
