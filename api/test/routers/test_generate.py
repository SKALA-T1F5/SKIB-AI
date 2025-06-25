from fastapi import APIRouter, HTTPException

from api.question.schemas.question import (
    DifficultyLevel,
    GradingCriterion,
    QuestionResponse,
    QuestionType,
)
from api.test.schemas.test_generate import (
    TestGenerationRequest,
    TestGenerationResponse,
)
from src.agents.question_generator.agent import QuestionGeneratorAgent

router = APIRouter(prefix="/api/test", tags=["Test"])


@router.post("/generate", response_model=TestGenerationResponse)
async def generate_test_questions(request: TestGenerationRequest):
    """
    QuestionGeneratorAgent를 사용한 문제 생성
    """
    try:
        # 1. QuestionGeneratorAgent 초기화
        agent = QuestionGeneratorAgent()

        # 2. 요청 데이터를 agent에 필요한 형태로 변환
        # 문서별 설정을 document_test_plan_data 형태로 변환
        document_plans = []
        for doc_config in request.document_configs:
            # 각 문서별 키워드는 별도로 관리되어야 하므로
            # 실제로는 문서 ID를 통해 키워드를 조회해야 합니다
            document_plan = {
                "document_name": f"document_{doc_config.documentId}",  # 실제로는 문서명 조회 필요
                "keywords": [],  # 실제로는 문서별 키워드 조회 필요
                "recommended_questions": {
                    "objective": doc_config.configured_objective_count,
                    "subjective": doc_config.configured_subjective_count,
                },
            }
            document_plans.append(document_plan)

        # 3. test_plan 데이터 구성
        total_test_plan_data = {
            "test_summary": request.summary,
            "difficulty": request.difficulty_level.value.lower(),
            "total_objective": sum(
                doc.configured_objective_count for doc in request.document_configs
            ),
            "total_subjective": sum(
                doc.configured_subjective_count for doc in request.document_configs
            ),
        }

        document_test_plan_data = {"document_plans": document_plans}

        # 4. Agent를 통한 문제 생성
        result = agent.generate_enhanced_questions_from_test_plans(
            total_test_plan_data=total_test_plan_data,
            document_test_plan_data=document_test_plan_data,
        )

        if result.get("status") == "failed":
            raise HTTPException(
                status_code=500, detail=result.get("error", "문제 생성 실패")
            )

        # 5. 생성된 문제를 QuestionResponse 형태로 변환
        questions = []
        generated_questions = result.get("questions", [])

        print(generated_questions)

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
                difficulty_level=difficulty,
                question=q.get("question", ""),
                options=(
                    q.get("options")
                    if question_type == QuestionType.objective
                    else None
                ),
                answer=q.get("answer", ""),
                explanation=q.get("explanation"),
                grading_criteria=grading_criteria,
                documentId=q.get("document_id", 0),  # 실제 문서 ID 매핑 필요
                document_name=q.get("document_source", ""),
                keywords=q.get("source_keywords", []),
                tags=q.get("tags", []),
            )
            questions.append(question_response)

        # 6. 응답 데이터 구성
        objective_count = len(
            [q for q in questions if q.type == QuestionType.objective]
        )
        subjective_count = len(
            [q for q in questions if q.type == QuestionType.subjective]
        )

        return TestGenerationResponse(
            questions=questions,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문제 생성 실패: {str(e)}")
