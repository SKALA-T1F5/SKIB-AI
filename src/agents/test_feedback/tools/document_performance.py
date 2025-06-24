from collections import defaultdict
from typing import List, Dict, Any


def calc_performance_by_document(question_results: List[Dict[str, Any]]):
    # performance 계산
    doc_map = defaultdict(list)
    for q in question_results:
        doc_map[q['documentName']].append(q)
    performance = []
    for doc, questions in doc_map.items():
        avg = sum(q['correctRate'] for q in questions) / len(questions)
        keywords = list({q['keyword'] for q in questions if 'keyword' in q})
        performance.append({
            "documentName": doc,
            "averageCorrectRate": round(avg, 2),
            "countQuestions": len(questions),  # 문서별 총 문제 개수 추가
            "keywords": keywords
        })
    
    # projectReadiness를 문서별 최소 정답률 기준으로 계산
    min_rate = min(doc['averageCorrectRate'] for doc in performance) if performance else 0
    if min_rate >= 90:
        project_readiness_result = "Excellent"
    elif min_rate >= 60:
        project_readiness_result = "Pass"
    else:
        project_readiness_result = "Fail"
    
    return performance, project_readiness_result 