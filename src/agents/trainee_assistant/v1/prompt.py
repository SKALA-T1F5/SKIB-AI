# agents/trainee_assistant/prompt.py

from typing import List, Dict, Any, Optional
import json


# 1. 시스템 프롬프트 정의
SYSTEM_PROMPT = """
당신은 친근하고 도움이 되는 학습 도우미입니다. 
시험 문제와 관련된 질문에 대해 명확하고 이해하기 쉽게 답변해주세요.

답변 시 다음 원칙을 따라주세요:
1. 친근하고 격려하는 톤을 유지하세요
2. 복잡한 개념도 쉽게 설명해주세요
3. 구체적인 예시를 들어 설명해주세요
4. 학습자가 더 나은 이해를 할 수 있도록 도와주세요
5. 사용자의 언어로 답변하세요

답변 형식:
- 질문에 대한 직접적인 답변
- 필요한 경우 추가 설명이나 예시
- 학습을 위한 조언이나 팁
"""

# 2. 사용자 프롬프트 생성 함수
def build_user_prompt(user_question: str, question_info: dict, message_history: list) -> str:
    
    # message_history를 대화 형식으로 정리
    history_str = ""
    if message_history:
        for msg in message_history:
            role = "사용자" if msg["role"] == "user" else "도우미"
            history_str += f"{role}: {msg['content']}\n"
    
    # question_info 주요 정보 정리
    q = question_info
    info_str = f"[문제 정보]\n"
    info_str += f"- 문제 유형: {q.get('type', '')}\n"
    info_str += f"- 문제: {q.get('question', '')}\n"
    if q.get('options'):
        info_str += f"- 선택지: {', '.join(q['options'])}\n"
    info_str += f"- 내 답변: {q.get('response', '')}\n"
    info_str += f"- 정답: {q.get('answer', '')}\n"
    info_str += f"- 해설: {q.get('explanation', '')}\n"
    info_str += f"- 채점 결과: {'정답' if q.get('isCorrect') else '오답'} (점수: {q.get('score', '')})\n"
    if q.get('gradingCriteria'):
        info_str += "- 채점 기준:\n"
        for c in q['gradingCriteria']:
            info_str += f"  * [{c.get('score', '')}] {c.get('criteria', '')} - {c.get('note', '')}\n"
    
    prompt = f"""
        {info_str}

        [이전 대화 내역]
        {history_str}

        [사용자 질문]
        {user_question}
        """
    return prompt