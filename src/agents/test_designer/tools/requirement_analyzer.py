"""
요구사항 분석 도구
사용자 프롬프트와 문서 정보를 분석하여 테스트 요구사항을 추출
"""

from typing import Dict, Any, List
import re


class RequirementAnalyzer:
    """요구사항 분석기"""
    
    def __init__(self):
        self.difficulty_keywords = {
            "easy": ["쉬운", "기초", "초급", "간단한", "기본"],
            "medium": ["중간", "보통", "일반적인", "표준"],
            "hard": ["어려운", "고급", "심화", "복잡한", "전문"]
        }
        
        self.test_type_keywords = {
            "objective": ["객관식", "선택형", "multiple choice"],
            "subjective": ["주관식", "서술형", "essay", "단답형"],
            "mixed": ["혼합", "객관식과 주관식", "다양한"]
        }
    
    def analyze(self, user_prompt: str, keywords: List[str], document_summary: str) -> Dict[str, Any]:
        """요구사항 종합 분석"""
        
        return {
            "difficulty": self._extract_difficulty(user_prompt),
            "test_type": self._extract_test_type(user_prompt),
            "question_count": self._extract_question_count(user_prompt),
            "time_limit": self._extract_time_limit(user_prompt),
            "focus_topics": self._extract_focus_topics(user_prompt, keywords),
            "special_requirements": self._extract_special_requirements(user_prompt)
        }
    
    def _extract_difficulty(self, prompt: str) -> str:
        """난이도 추출"""
        prompt_lower = prompt.lower()
        
        for difficulty, keywords in self.difficulty_keywords.items():
            for keyword in keywords:
                if keyword in prompt_lower:
                    return difficulty
        
        return "medium"  # 기본값
    
    def _extract_test_type(self, prompt: str) -> str:
        """테스트 유형 추출"""
        prompt_lower = prompt.lower()
        
        has_objective = any(keyword in prompt_lower for keyword in self.test_type_keywords["objective"])
        has_subjective = any(keyword in prompt_lower for keyword in self.test_type_keywords["subjective"])
        
        if has_objective and has_subjective:
            return "mixed"
        elif has_objective:
            return "objective"
        elif has_subjective:
            return "subjective"
        else:
            return "mixed"  # 기본값
    
    def _extract_question_count(self, prompt: str) -> Dict[str, int]:
        """문제 수 추출"""
        result = {"objective": 5, "subjective": 3}  # 기본값
        
        # 객관식 문제 수 찾기
        obj_patterns = [
            r'객관식.*?(\d+).*?개',
            r'선택형.*?(\d+).*?문',
            r'(\d+).*?객관식'
        ]
        
        for pattern in obj_patterns:
            match = re.search(pattern, prompt)
            if match:
                result["objective"] = int(match.group(1))
                break
        
        # 주관식 문제 수 찾기
        subj_patterns = [
            r'주관식.*?(\d+).*?개',
            r'서술형.*?(\d+).*?문',
            r'(\d+).*?주관식'
        ]
        
        for pattern in subj_patterns:
            match = re.search(pattern, prompt)
            if match:
                result["subjective"] = int(match.group(1))
                break
        
        # 전체 문제 수만 언급된 경우
        total_patterns = [
            r'총.*?(\d+).*?문',
            r'(\d+).*?문제',
            r'문제.*?(\d+).*?개'
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, prompt)
            if match:
                total = int(match.group(1))
                # 비율로 분배 (객관식 60%, 주관식 40%)
                result["objective"] = int(total * 0.6)
                result["subjective"] = int(total * 0.4)
                break
        
        return result
    
    def _extract_time_limit(self, prompt: str) -> int:
        """제한시간 추출 (분 단위)"""
        time_patterns = [
            r'(\d+)분',
            r'(\d+)시간',
            r'제한시간.*?(\d+)',
            r'시간.*?(\d+)'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, prompt)
            if match:
                time_value = int(match.group(1))
                # 시간 단위면 분으로 변환
                if '시간' in pattern:
                    return time_value * 60
                return time_value
        
        return 60  # 기본값: 60분
    
    def _extract_focus_topics(self, prompt: str, keywords: List[str]) -> List[str]:
        """집중 주제 추출"""
        focus_topics = []
        
        # 프롬프트에서 키워드와 매칭되는 주제 찾기
        prompt_lower = prompt.lower()
        
        for keyword in keywords:
            if keyword.lower() in prompt_lower:
                focus_topics.append(keyword)
        
        # 특정 주제 언급 패턴 찾기
        topic_patterns = [
            r'(\w+)에.*?대한',
            r'(\w+).*?중심',
            r'(\w+).*?위주',
            r'특히.*?(\w+)'
        ]
        
        for pattern in topic_patterns:
            matches = re.findall(pattern, prompt)
            focus_topics.extend(matches)
        
        return list(set(focus_topics))  # 중복 제거
    
    def _extract_special_requirements(self, prompt: str) -> List[str]:
        """특수 요구사항 추출"""
        requirements = []
        
        special_keywords = {
            "실무중심": ["실무", "실제", "현장", "업무"],
            "이론중심": ["이론", "개념", "정의", "원리"],
            "응용문제": ["응용", "활용", "적용", "사례"],
            "암기문제": ["암기", "기억", "외우", "단순"],
            "분석문제": ["분석", "해석", "평가", "비교"],
            "창의문제": ["창의", "창조", "발상", "아이디어"]
        }
        
        prompt_lower = prompt.lower()
        
        for req_type, keywords in special_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                requirements.append(req_type)
        
        return requirements