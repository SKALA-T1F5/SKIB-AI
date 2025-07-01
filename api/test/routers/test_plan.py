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
        test_summary_data = result.get("test_summary", {})
        test_title = test_summary_data.get("name", "")
        test_summary_text = test_summary_data.get("test_summary", "")

        # 난이도 매핑 (test_summary에서 가져오기)
        difficulty_mapping = {
            "EASY": DifficultyLevel.easy,
            "NORMAL": DifficultyLevel.normal,
            "HARD": DifficultyLevel.hard,
        }

        # Gemini가 반환한 difficulty_level 사용
        gemini_difficulty = test_summary_data.get("difficulty_level", "NORMAL")
        difficulty_level = difficulty_mapping.get(gemini_difficulty, DifficultyLevel.normal)

        # Gemini가 추천한 문제 수 사용 (document_configs에서 추출)
        document_configs_from_gemini = test_summary_data.get("document_configs", [])
        total_objective = sum(config.get("recommended_objective", 0) for config in document_configs_from_gemini)
        total_subjective = sum(config.get("recommended_subjective", 0) for config in document_configs_from_gemini)
        
        # 기본값 설정 (Gemini 추천이 없을 경우)
        if total_objective == 0:
            total_objective = test_config.get("num_objective", 5)
        if total_subjective == 0:
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
                        documentName=getattr(doc_summary, "name", ""),
                        keywords=doc_summary.keywords,
                        configuredObjectiveCount=obj_count,
                        configuredSubjectiveCount=subj_count,
                    )
                )

        # 응답 생성 (Gemini 결과 활용)
        response = TestPlanResponse(
            name=test_title,
            summary=test_summary_text,
            difficultyLevel=difficulty_level,
            limitedTime=test_summary_data.get("limited_time", 60),
            passScore=test_summary_data.get("pass_score", 70),
            isRetake=test_summary_data.get("retake", True),
            documentConfigs=document_configs,
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"테스트 계획 생성 실패: {str(e)}")
