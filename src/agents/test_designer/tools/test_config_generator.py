"""
테스트 설정 생성 도구
분석된 요구사항을 바탕으로 구체적인 테스트 설정을 생성
"""

import json
from typing import Any, Dict, List


class TestConfigGenerator:
    """테스트 설정 생성기"""

    def __init__(self):
        self.difficulty_configs = {
            "easy": {
                "max_questions": 15,
                "min_time_per_question": 2,
                "complexity_level": 1,
            },
            "medium": {
                "max_questions": 20,
                "min_time_per_question": 3,
                "complexity_level": 2,
            },
            "hard": {
                "max_questions": 25,
                "min_time_per_question": 4,
                "complexity_level": 3,
            },
        }

        self.scoring_templates = {
            "objective": {"points": 2, "partial_credit": False},
            "subjective": {"points": 5, "partial_credit": True},
        }

    def generate_config(
        self, requirements: Dict[str, Any], test_summary: str
    ) -> Dict[str, Any]:
        """테스트 설정 생성"""

        difficulty = requirements.get("difficulty", "medium")
        test_type = requirements.get("test_type", "mixed")
        question_count = requirements.get(
            "question_count", {"objective": 5, "subjective": 3}
        )
        time_limit = requirements.get("time_limit", 60)

        config = {
            "test_info": {
                "title": self._generate_test_title(requirements),
                "description": test_summary,
                "difficulty": difficulty,
                "type": test_type,
                "estimated_duration": time_limit,
            },
            "question_config": {
                "total_questions": question_count["objective"]
                + question_count["subjective"],
                "objective_questions": question_count["objective"],
                "subjective_questions": question_count["subjective"],
                "distribution": self._calculate_distribution(question_count),
            },
            "scoring_config": self._generate_scoring_config(question_count),
            "generation_config": self._generate_generation_config(requirements),
            "constraints": self._generate_constraints(requirements, difficulty),
            "metadata": {
                "created_from": "test_designer_agent",
                "requirements": requirements,
                "version": "1.0",
            },
        }

        return config

    def _generate_test_title(self, requirements: Dict[str, Any]) -> str:
        """테스트 제목 생성"""
        difficulty = requirements.get("difficulty", "medium")
        focus_topics = requirements.get("focus_topics", [])

        difficulty_map = {"easy": "기초", "medium": "중급", "hard": "고급"}

        if focus_topics:
            main_topic = focus_topics[0]
            return f"{main_topic} {difficulty_map[difficulty]} 평가"
        else:
            return f"문서 기반 {difficulty_map[difficulty]} 평가"

    def _calculate_distribution(
        self, question_count: Dict[str, int]
    ) -> Dict[str, float]:
        """문제 유형별 분포 계산"""
        total = question_count["objective"] + question_count["subjective"]

        if total == 0:
            return {"objective": 0.0, "subjective": 0.0}

        return {
            "objective": round(question_count["objective"] / total, 2),
            "subjective": round(question_count["subjective"] / total, 2),
        }

    def _generate_scoring_config(
        self, question_count: Dict[str, int]
    ) -> Dict[str, Any]:
        """채점 설정 생성"""
        obj_points = self.scoring_templates["objective"]["points"]
        subj_points = self.scoring_templates["subjective"]["points"]

        total_points = (question_count["objective"] * obj_points) + (
            question_count["subjective"] * subj_points
        )

        return {
            "objective": {
                "points_per_question": obj_points,
                "total_points": question_count["objective"] * obj_points,
                "partial_credit": False,
            },
            "subjective": {
                "points_per_question": subj_points,
                "total_points": question_count["subjective"] * subj_points,
                "partial_credit": True,
            },
            "total_points": total_points,
            "passing_score": total_points * 0.6,  # 60% 이상
            "grading_scale": {
                "A": total_points * 0.9,
                "B": total_points * 0.8,
                "C": total_points * 0.7,
                "D": total_points * 0.6,
                "F": 0,
            },
        }

    def _generate_generation_config(
        self, requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """문제 생성 설정"""
        difficulty = requirements.get("difficulty", "medium")
        special_reqs = requirements.get("special_requirements", [])
        focus_topics = requirements.get("focus_topics", [])

        return {
            "difficulty_level": difficulty,
            "focus_topics": focus_topics,
            "question_styles": self._determine_question_styles(special_reqs),
            "content_emphasis": self._determine_content_emphasis(special_reqs),
            "generation_strategy": "balanced",
            "quality_checks": [
                "difficulty_consistency",
                "topic_coverage",
                "answer_clarity",
                "distractor_quality",
            ],
        }

    def _determine_question_styles(self, special_requirements: List[str]) -> List[str]:
        """특수 요구사항에 따른 문제 스타일 결정"""
        styles = []

        style_mapping = {
            "실무중심": ["case_study", "practical_application"],
            "이론중심": ["definition", "concept_explanation"],
            "응용문제": ["application", "problem_solving"],
            "암기문제": ["recall", "recognition"],
            "분석문제": ["analysis", "comparison"],
            "창의문제": ["creative_thinking", "open_ended"],
        }

        for req in special_requirements:
            if req in style_mapping:
                styles.extend(style_mapping[req])

        if not styles:
            styles = ["balanced", "standard"]

        return list(set(styles))

    def _determine_content_emphasis(
        self, special_requirements: List[str]
    ) -> Dict[str, float]:
        """내용 강조점 결정"""
        emphasis = {
            "facts": 0.3,
            "concepts": 0.3,
            "procedures": 0.2,
            "applications": 0.2,
        }

        # 특수 요구사항에 따라 조정
        if "이론중심" in special_requirements:
            emphasis["concepts"] += 0.2
            emphasis["facts"] += 0.1
            emphasis["applications"] -= 0.15
            emphasis["procedures"] -= 0.15

        elif "실무중심" in special_requirements:
            emphasis["applications"] += 0.2
            emphasis["procedures"] += 0.15
            emphasis["concepts"] -= 0.15
            emphasis["facts"] -= 0.2

        elif "응용문제" in special_requirements:
            emphasis["applications"] += 0.3
            emphasis["procedures"] += 0.1
            emphasis["facts"] -= 0.2
            emphasis["concepts"] -= 0.2

        return emphasis

    def _generate_constraints(
        self, requirements: Dict[str, Any], difficulty: str
    ) -> Dict[str, Any]:
        """생성 제약조건"""
        difficulty_config = self.difficulty_configs[difficulty]

        return {
            "max_questions_per_topic": 5,
            "min_questions_per_topic": 1,
            "max_similar_questions": 2,
            "complexity_level": difficulty_config["complexity_level"],
            "time_constraints": {
                "max_time_per_question": difficulty_config["min_time_per_question"] * 2,
                "min_time_per_question": difficulty_config["min_time_per_question"],
            },
            "content_constraints": {
                "avoid_ambiguous": True,
                "require_single_correct": True,
                "minimum_distractor_quality": 0.7,
            },
        }

    def save_config(self, config: Dict[str, Any], filepath: str) -> bool:
        """설정을 파일로 저장"""
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"설정 저장 실패: {e}")
            return False

    def load_config(self, filepath: str) -> Dict[str, Any]:
        """파일에서 설정 로드"""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"설정 로드 실패: {e}")
            return {}
