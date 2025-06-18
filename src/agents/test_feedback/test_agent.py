# agents/test_feedback/test_agent.py
import sys
import os
import time
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

import asyncio
from src.agents.test_feedback.agent import test_feedback
from src.agents.test_feedback.example_data import exam_goal, question_results
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
