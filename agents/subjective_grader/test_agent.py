# agents/subjective_grader/test_agent.py
import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import asyncio
from agents.subjective_grader.agent import subjective_grader
from api.grading.schemas.subjective_grading import GradingCriterion

async def run_test():
    # 1. 예시 grading criteria
    test_grading_criteria = [
        GradingCriterion(score=0, criteria="관련 없는 설명", example=".", note="관련 없는 설명"),
        GradingCriterion(score=1, criteria="AI와 ML의 구분이 없는 설명", example="AI는 똑똑한 기술이에요", note="구분 없이 추상적으로 설명"),
        GradingCriterion(score=3, criteria="AI와 ML의 기본적 구분 설명", example="AI는 넓은 개념이고 ML은 그 하위", note="틀리진 않지만 설명이 짧음"),
        GradingCriterion(score=5, criteria="AI와 ML의 관계 및 차이를 구체적으로 설명", example="AI는 포괄 개념, ML은 데이터 학습 기반 기술", note="정확하고 구체적인 설명"),
    ]

    # 2. 예시 user_answer
    test_user_answer = "잘 모르겠어요" # 0점 수준
    # test_user_answer = "AI는 사람처럼 생각하는 기술이고, 요즘 많이 쓰여요." # 1점 수준
    # test_user_answer = "AI는 넓은 개념이고 머신러닝은 AI 안에 포함되는 기술이에요." # 3점 수준
    # test_user_answer = "AI는 인간의 지능을 모방하는 기술 전반을 말하고, 머신러닝은 그 중 데이터를 학습해서 스스로 규칙을 찾아내는 알고리즘 기반 기술입니다." # 5점 수준

    # 3. 채점 실행
    start_time = time.time()
    score = await subjective_grader(test_user_answer, test_grading_criteria)
    elapsed_time = time.time() - start_time

    # 4. 결과 출력
    print(f"🟨 응답 시간: {elapsed_time:.2f}초")
    print("🟨 user_answer:", test_user_answer)
    print("🟨 grading_criteria:")
    for c in test_grading_criteria:
        print(f"└─ {c}")
    print("✅ 결과 점수:", score)

if __name__ == "__main__":
    asyncio.run(run_test())
