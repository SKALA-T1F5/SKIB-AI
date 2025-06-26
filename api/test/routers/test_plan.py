from fastapi import APIRouter, HTTPException

from api.question.schemas.question import DifficultyLevel
from api.test.schemas.test_plan import (
    TestPlanByDocument,
    TestPlanRequest,
    TestPlanResponse,
)
from src.agents.test_designer.agent import TestDesignerAgent

router = APIRouter(prefix="/api/test", tags=["Test"])


@router.post("/plan", response_model=TestPlanResponse)
async def generate_test_plan(request: TestPlanRequest):
    """
    테스트 계획 생성
    - 문서 요약과 사용자 입력을 바탕으로 테스트 구조 추천
    """
    try:
        # 모든 문서의 키워드와 요약 합치기
        all_keywords = []
        all_summaries = []

        for doc_summary in request.document_summaries:
            all_keywords.extend(doc_summary.keywords)
            all_summaries.append(
                f"문서 {doc_summary.document_id}: {doc_summary.summary}"
            )

        # 중복 키워드 제거
        unique_keywords = list(set(all_keywords))
        combined_summary = "\n\n".join(all_summaries)

        # TestDesigner Agent 직접 실행 (asyncio.run 제거)
        agent = TestDesignerAgent()
        await agent.initialize()

        # TestDesigner Agent 실행
        input_data = {
            "keywords": unique_keywords,
            "document_summary": combined_summary,
            "document_topics": unique_keywords[:5],  # 상위 5개 키워드를 주제로 사용
            "user_prompt": request.user_input,
            "difficulty": "medium",  # 기본값, Agent가 조정할 수 있음
            "test_type": "mixed",
            "time_limit": 60,
        }

        result = await agent.execute(input_data)

        # Agent 결과에서 필요한 정보 추출
        test_config = result.get("test_config", {})
        test_summary = result.get("test_summary", {})
        test_title = test_summary.get("name", "")
        test_summary = test_summary.get("test_summary", "")

        # 난이도 매핑
        difficulty_mapping = {
            "easy": DifficultyLevel.easy,
            "medium": DifficultyLevel.normal,
            "hard": DifficultyLevel.hard,
        }

        difficulty_level = difficulty_mapping.get(
            test_config.get("difficulty", "medium"), DifficultyLevel.normal
        )

        # 문서별 문항 수 배분 계산
        total_objective = test_config.get("num_objective", 5)
        total_subjective = test_config.get("num_subjective", 3)
        document_count = len(request.document_summaries)

        document_configs = []

        if document_count > 0:
            # 문서별로 균등 배분 (나머지는 첫 번째 문서에 추가)
            base_objective = total_objective // document_count
            base_subjective = total_subjective // document_count
            remainder_objective = total_objective % document_count
            remainder_subjective = total_subjective % document_count

            for i, doc_summary in enumerate(request.document_summaries):
                obj_count = base_objective + (1 if i < remainder_objective else 0)
                subj_count = base_subjective + (1 if i < remainder_subjective else 0)

                document_configs.append(
                    TestPlanByDocument(
                        documentId=doc_summary.document_id,
                        documentName=getattr(doc_summary, "document_name", ""),
                        keywords=doc_summary.keywords,
                        configuredObjectiveCount=obj_count,
                        configuredSubjectiveCount=subj_count,
                    )
                )

        # 응답 생성
        # TODO: 현재 state 맞게 출력되고 있는지 확인 X
        response = TestPlanResponse(
            name=test_title,
            summary=test_summary,
            difficultyLevel=difficulty_level,
            limitedTime=test_config.get("time_limit", 60),
            passScore=test_config.get("pass_score", 70),
            isRetake=test_config.get("retake_allowed", True),
            documentConfigs=document_configs,
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 계획 생성 실패: {str(e)}")
