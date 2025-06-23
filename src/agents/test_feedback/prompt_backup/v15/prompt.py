# agents/test_feedback/prompt.py
# v15 : Output Example 삭제

from typing import List, Dict, Any
import json


# 1. 시스템 프롬프트 정의
# AI의 역할과 응답 형식을 지정합니다.
SYSTEM_PROMPT = """
[Role]
당신은 학습 성과를 분석하고, 해당 결과를 바탕으로 프로젝트 수행 가능 여부를 전략적으로 판단하는 교육 평가 전문가입니다.

[Task]
시험 결과를 분석하여 아래 항목을 JSON 형식으로 작성하세요:
1. examGoal: 시험 목표를 40자 이내로 요약
2. performanceByDocument: 각 문서별 평균 정답률과 실무 관점 코멘트
3. insights: 반드시 총 4개 (강점/약점 비율은 조정 가능, 단 최소 1개씩은 포함해야 함)
   - 문항의 questionText와 '#keyword'를 참고해 개념 관점에서 text 작성
   - 예: "'#지식베이스'와 검색 '#알고리즘'의 역할 구분이 불명확함"
4. improvementPoints: 실무 중심의 구체적인 개선 방안
5. suggestedTopics: 실습 또는 구성요소 수준의 주제 3개 (예: "법령 적용 사례 비교 학습" 등)
6. overallEvaluation: ProjectReadiness를 종합적으로 평가하여 작성합니다.

[Output Format]
{
    "examGoal": "...",
    "performanceByDocument": [
        {
            "documentName":"...",
            "averageCorrectRate": number,
            "comment": "..."
        },
        ...
     ],
    "insights": [
        {"type": "strength/weakness","text": "..."},
        {"type": "strength/weakness","text": "..."},
        {"type": "strength/weakness","text": "..."},
        {"type": "strength/weakness","text": "..."},
    ],
    "improvementPoints": "...",
    "suggestedTopics": [...],
    "overallEvaluation": "..."
}


"""

# 2. 사용자 프롬프트 생성 함수
# 시험목표와 선택된 문항별응시결과, 문서별 집계정보를 받아 AI가 이해할 수 있는 프롬프트 문자열을 생성
def build_user_prompt(exam_goal: str, selected_questions: List[Dict[str, Any]], performance_by_document: List[Dict[str, Any]]) -> str:
    # 문항별 결과를 문자열로 변환
    questions_text = ""
    for result in selected_questions:
        questions_text += f"""
        documentName: {result.get('documentName', 'N/A')} | questionText: {result.get('questionText', 'N/A')[:100]}... | tags: {result.get('tags', 'N/A')} | correctRate: {result.get('correctRate', 'N/A')}% | #keyword: {result.get('keyword', 'N/A')}
        """
    
    prompt = f"""
        [시험 목표]
        \"\"\"{exam_goal}\"\"\"

        [문서별 결과]
        {json.dumps(performance_by_document, ensure_ascii=False, indent=2)}

        [문항별 결과 (상하위 5개씩)]
        {questions_text}
        
        위 정보를 기반으로 학습자의 강점/약점, 개선점, 프로젝트 참여 적정성을 포함한 피드백을 다음 JSON 형식으로 제공하세요.
        """
    
    return prompt