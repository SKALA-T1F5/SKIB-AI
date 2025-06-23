# agents/test_feedback/test_agent.py
import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import asyncio
from src.agents.test_feedback.agent import test_feedback
from src.agents.test_feedback.example_data.example_data_1 import exam_goal, question_results
# from src.agents.test_feedback.example_data.example_data_2 import exam_goal, question_results
# from src.agents.test_feedback.example_data.example_data_3 import exam_goal, question_results
# from api.grading.schemas.subjective_grading import GradingCriterion

async def run_test():
    # 1. 시험 목표와 문항별 응시 결과는 example_data.py에서 가져옴
    print(f"🟨 시험 목표: {exam_goal}")
    print(f"🟨 문항 수: {len(question_results)}개")

    # 2. 테스트 실행
    start_time = time.time()
    result = await test_feedback(exam_goal, question_results)
    elapsed_time = time.time() - start_time

    # 3. 결과 출력
    print(f"🟨 응답 시간: {elapsed_time:.2f}초")
    print("\n" + "="*80)
    
    print(f"\n1️⃣ 전체 평가:")
    print(f"  {result['overallEvaluation']}")

    print(f"2️⃣ 시험 목표: {result['examGoal']}")
    
    print(f"\n3️⃣ 문서별 성과:")
    for doc in result['performanceByDocument']:
        print(f"  • {doc['documentName']}")
        print(f"    - 평균 정답률: {doc['averageCorrectRate']}%")
        print(f"    - 평가: {doc['comment']}")
    
    print(f"\n4️⃣ 인사이트 분석:")
    strengths = [ins['text'] for ins in result.get('insights', []) if ins.get('type') == 'strength']
    weaknesses = [ins['text'] for ins in result.get('insights', []) if ins.get('type') == 'weakness']
    print(f"\n└─ 강점:")
    for strength in strengths:
        print(f"  • {strength}")
    print(f"\n└─ 약점:")
    for weakness in weaknesses:
        print(f"  • {weakness}")
    
    print(f"\n└─ 개선점:")
    print(f"  {result['improvementPoints']}")
    
    project_readiness = result['projectReadiness']
    print(f"\n5️⃣ 프로젝트 참여 적정성: {project_readiness['result']} ")
    print(f"\n└─ 판단 근거: {project_readiness['reasoning']}")
    
    print(f"\n6️⃣ 추가 학습 주제:")
    for topic in result['suggestedTopics']:
        print(f"  • {topic}")
    

if __name__ == "__main__":
    asyncio.run(run_test())
