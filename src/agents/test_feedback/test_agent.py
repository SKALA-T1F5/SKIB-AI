# agents/test_feedback/test_agent.py
import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import asyncio
from src.agents.test_feedback.agent import test_feedback
# from api.grading.schemas.subjective_grading import GradingCriterion

async def run_test():
    # 1. 시험 목표
    test_goal = "AI와 머신러닝의 기본 개념과 관계를 이해하고 설명할 수 있는지 평가"

    # 2. 문항별 응시 결과
    question_results = [
        {
            "student_answer": "AI는 사람처럼 생각하는 기술이고, 요즘 많이 쓰여요.",
            "correct_answer": "AI(인공지능)는 인간의 지능을 모방하는 기술 전반을 의미하는 포괄적인 개념입니다.",
            "score": 25,
            "criteria": "AI와 ML의 구분이 없는 설명 - 25점"
        },
        {
            "student_answer": "머신러닝은 AI 안에 포함되는 기술이에요.",
            "correct_answer": "머신러닝은 AI의 한 분야로, 데이터를 학습하여 패턴을 발견하고 예측을 수행하는 알고리즘 기반 기술입니다.",
            "score": 50,
            "criteria": "AI와 ML의 기본적 구분 설명 - 50점"
        },
        {
            "student_answer": "AI는 인간의 지능을 모방하는 기술 전반을 말하고, 머신러닝은 그 중 데이터를 학습해서 스스로 규칙을 찾아내는 알고리즘 기반 기술입니다.",
            "correct_answer": "AI(인공지능)는 인간의 지능을 모방하는 기술 전반을 의미하는 포괄적인 개념입니다. 머신러닝은 AI의 한 분야로, 데이터를 학습하여 패턴을 발견하고 예측을 수행하는 알고리즘 기반 기술입니다.",
            "score": 85,
            "criteria": "AI와 ML의 관계 및 차이를 구체적으로 설명 - 85점"
        },
        {
            "student_answer": "딥러닝에 대해서는 잘 모르겠어요.",
            "correct_answer": "딥러닝은 머신러닝의 하위 분야로, 신경망을 사용하여 복잡한 패턴을 학습합니다.",
            "score": 0,
            "criteria": "딥러닝 개념 미이해 - 0점"
        }
    ]

    # 3. 테스트 실행
    start_time = time.time()
    result = await test_feedback(test_goal, question_results)
    elapsed_time = time.time() - start_time

    # 4. 결과 출력
    print(f"🟨 응답 시간: {elapsed_time:.2f}초")
    print(f"🟨 시험 목표: {test_goal}")
    print(f"🟨 문항 수: {len(question_results)}개")
    print("\n" + "="*60)
    print("📊 시험 결과 분석")
    print("="*60)
    print(f"✅ 전체 점수: {result['overall_score']}/100")
    print(f"✅ 성취 수준: {result['achievement_level']}")
    
    print(f"\n🎯 강점:")
    for strength in result['test_analysis']['strengths']:
        print(f"  • {strength}")
    
    print(f"\n⚠️  약점:")
    for weakness in result['test_analysis']['weaknesses']:
        print(f"  • {weakness}")
    
    print(f"\n📈 개선 영역:")
    for area in result['test_analysis']['improvement_areas']:
        print(f"  • {area}")
    
    print(f"\n💡 상세 피드백:")
    print(f"  • 전체 성과: {result['detailed_feedback']['overall_performance']}")
    print(f"  • 목표 달성도: {result['detailed_feedback']['goal_achievement']}")
    
    print(f"\n🔍 문항별 분석:")
    for analysis in result['question_analysis']:
        print(f"  • 문항 {analysis['question_id']}: {analysis['performance']}")
        print(f"    제안: {analysis['suggestion']}")
    
    print(f"\n📋 권장사항:")
    for rec in result['detailed_feedback']['recommendations']:
        print(f"  • {rec}")

if __name__ == "__main__":
    asyncio.run(run_test())
