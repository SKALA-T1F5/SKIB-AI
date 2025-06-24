from typing import List, Dict, Any


def select_top_bottom_questions(question_results: List[Dict[str, Any]], top_count: int = 5, bottom_count: int = 5) -> List[Dict[str, Any]]:
    """
    전체 문제 중 정답률 기준 상위 5개, 하위 5개 문제를 선택하여 총 10개 문제를 반환
    """
    # 정답률 기준으로 전체 문제 정렬
    sorted_questions = sorted(question_results, key=lambda x: x['correctRate'], reverse=True)
    
    selected_questions = []
    
    # 상위 5개 선택
    top_questions = sorted_questions[:top_count]
    selected_questions.extend(top_questions)
    
    # 하위 5개 선택 (중복 방지)
    if len(sorted_questions) > top_count + bottom_count:
        bottom_questions = sorted_questions[-(bottom_count):]
    elif len(sorted_questions) > top_count:
        bottom_questions = sorted_questions[top_count:]
    else:
        bottom_questions = []
    
    selected_questions.extend(bottom_questions)
    
    return selected_questions 