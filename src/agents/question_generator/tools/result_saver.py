"""
결과 저장 관련 도구
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any


class ResultSaver:
    """문제 생성 결과 저장 클래스"""
    
    @staticmethod
    def save_enhanced_questions(
        questions: List[Dict], 
        summary: Dict,
        total_plan: Dict,
        document_plan: Dict
    ) -> Dict[str, Any]:
        """향상된 문제 생성 결과 저장 (기본/여분 문제 분리)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 기본 문제와 여분 문제 분리
        basic_questions = [q for q in questions if q.get('generation_type') == 'basic']
        extra_questions = [q for q in questions if q.get('generation_type') == 'advanced']
        
        # 공통 메타데이터
        common_metadata = {
            "generation_info": {
                "method": "enhanced_vector_search",
                "generated_at": datetime.now().isoformat(),
                "generation_summary": summary,
                "test_plans_used": {
                    "total_plan_name": total_plan.get('test_plan', {}).get('name'),
                    "document_count": summary['total_documents']
                }
            }
        }
        
        output_dir = "data/outputs/generated_questions"
        os.makedirs(output_dir, exist_ok=True)
        files_created = []
        
        # 1. 기본 문제 저장
        if basic_questions:
            basic_data = {
                **common_metadata,
                "question_type": "basic",
                "total_questions": len(basic_questions),
                "questions_by_document": {},
                "all_questions": basic_questions
            }
            
            # 문서별 기본 문제 분류
            for question in basic_questions:
                doc_name = question.get('document_source', 'Unknown')
                if doc_name not in basic_data["questions_by_document"]:
                    basic_data["questions_by_document"][doc_name] = []
                basic_data["questions_by_document"][doc_name].append(question)
            
            basic_file = f"{output_dir}/basic_questions_{timestamp}.json"
            with open(basic_file, 'w', encoding='utf-8') as f:
                json.dump(basic_data, f, ensure_ascii=False, indent=2)
            files_created.append(basic_file)
            print(f"💾 기본 문제 저장: {basic_file}")
            print(f"📈 기본 문제 수: {len(basic_questions)}개")
        
        # 2. 여분 문제 저장
        if extra_questions:
            extra_data = {
                **common_metadata,
                "question_type": "extra",
                "total_questions": len(extra_questions),
                "questions_by_document": {},
                "all_questions": extra_questions
            }
            
            # 문서별 여분 문제 분류
            for question in extra_questions:
                doc_name = question.get('document_source', 'Unknown')
                if doc_name not in extra_data["questions_by_document"]:
                    extra_data["questions_by_document"][doc_name] = []
                extra_data["questions_by_document"][doc_name].append(question)
            
            extra_file = f"{output_dir}/extra_questions_{timestamp}.json"
            with open(extra_file, 'w', encoding='utf-8') as f:
                json.dump(extra_data, f, ensure_ascii=False, indent=2)
            files_created.append(extra_file)
            print(f"💾 여분 문제 저장: {extra_file}")
            print(f"🎯 여분 문제 수: {len(extra_questions)}개")
        
        
        print(f"\n📊 총 문제 수: {len(questions)}개")
        print(f"📈 기본 문제: {len(basic_questions)}개")
        print(f"🎯 여분 문제: {len(extra_questions)}개")
        print(f"📁 생성된 파일: {len(files_created)}개")
        
        return {
            "status": "completed",
            "total_questions": len(questions),
            "basic_questions_count": len(basic_questions),
            "extra_questions_count": len(extra_questions),
            "summary": summary,
            "questions": questions,
            "files_created": files_created,
            "file_details": {
                "basic_file": files_created[0] if basic_questions else None,
                "extra_file": files_created[1] if extra_questions and len(files_created) > 1 else files_created[0] if extra_questions else None
            }
        }
    
    @staticmethod
    def save_standard_question_results(
        questions: List[Dict],
        source_file: str,
        keywords: List[str],
        main_topics: List[str],
        summary: str
    ) -> List[str]:
        """표준 형식으로 문제 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.splitext(os.path.basename(source_file))[0]
        files_created = []

        # 1. 생성된 문제 파일 저장
        questions_dir = "data/outputs/generated_questions"
        os.makedirs(questions_dir, exist_ok=True)

        questions_data = {
            "test_info": {
                "source_file": source_file,
                "generation_date": datetime.now().isoformat(),
                "test_type": "auto_generated",
            },
            "question_summary": {
                "total_questions": len(questions),
                "objective_questions": len(
                    [q for q in questions if q.get("type") == "OBJECTIVE"]
                ),
                "subjective_questions": len(
                    [q for q in questions if q.get("type") == "SUBJECTIVE"]
                ),
                "difficulty_distribution": {
                    "easy": len(
                        [q for q in questions if q.get("difficulty_level") == "EASY"]
                    ),
                    "normal": len(
                        [q for q in questions if q.get("difficulty_level") == "NORMAL"]
                    ),
                    "hard": len(
                        [q for q in questions if q.get("difficulty_level") == "HARD"]
                    ),
                },
            },
            "questions": questions,
            "source_keywords": keywords,
            "source_topics": main_topics,
        }

        questions_file = f"{questions_dir}/{filename}_questions_{timestamp}.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(questions_data, f, ensure_ascii=False, indent=2)
        print(f"💾 생성된 문제 저장: {questions_file}")
        files_created.append(questions_file)

        # 2. 테스트 요약 파일 생성
        summary_file = ResultSaver._save_test_summary(
            questions, source_file, keywords, main_topics, summary, timestamp
        )
        if summary_file:
            files_created.append(summary_file)

        # 3. 테스트 config 파일 생성
        config_file = ResultSaver._save_test_config(questions, source_file, timestamp)
        if config_file:
            files_created.append(config_file)

        return files_created
    
    @staticmethod
    def _save_test_summary(
        questions: List[Dict],
        source_file: str,
        keywords: List[str],
        main_topics: List[str],
        summary: str,
        timestamp: str,
    ) -> str:
        """테스트 요약 파일 저장"""
        try:
            filename = os.path.splitext(os.path.basename(source_file))[0]
            summary_dir = "data/outputs/test_summaries"
            os.makedirs(summary_dir, exist_ok=True)

            objective_questions = [q for q in questions if q.get("type") == "OBJECTIVE"]
            subjective_questions = [
                q for q in questions if q.get("type") == "SUBJECTIVE"
            ]

            test_summary_data = {
                "test_overview": {
                    "title": f"{filename} - 자동 생성 테스트",
                    "description": f"'{filename}' 문서를 기반으로 AI가 자동 생성한 평가 테스트입니다.",
                    "source_document": source_file,
                    "creation_date": datetime.now().isoformat(),
                    "test_type": "종합 평가",
                    "estimated_duration": f"{max(30, len(questions) * 2)}분",
                },
                "content_analysis": {
                    "document_summary": (
                        summary[:300] + "..." if len(summary) > 300 else summary
                    ),
                    "key_concepts": keywords[:10],
                    "main_topics": main_topics[:5],
                    "content_complexity": ResultSaver._analyze_content_complexity(
                        keywords, main_topics, questions
                    ),
                },
                "test_structure": {
                    "total_questions": len(questions),
                    "question_breakdown": {
                        "objective": {
                            "count": len(objective_questions),
                            "percentage": (
                                round(
                                    len(objective_questions) / len(questions) * 100, 1
                                )
                                if questions
                                else 0
                            ),
                            "focus_areas": ResultSaver._extract_question_topics(
                                objective_questions
                            ),
                        },
                        "subjective": {
                            "count": len(subjective_questions),
                            "percentage": (
                                round(
                                    len(subjective_questions) / len(questions) * 100, 1
                                )
                                if questions
                                else 0
                            ),
                            "focus_areas": ResultSaver._extract_question_topics(
                                subjective_questions
                            ),
                        },
                    },
                    "difficulty_distribution": {
                        "easy": len(
                            [
                                q
                                for q in questions
                                if q.get("difficulty_level") == "EASY"
                            ]
                        ),
                        "normal": len(
                            [
                                q
                                for q in questions
                                if q.get("difficulty_level") == "NORMAL"
                            ]
                        ),
                        "hard": len(
                            [
                                q
                                for q in questions
                                if q.get("difficulty_level") == "HARD"
                            ]
                        ),
                    },
                },
                "assessment_guidelines": {
                    "objective_scoring": "각 객관식 문항당 1점, 정답/오답으로 채점",
                    "subjective_scoring": "문항별 배점에 따라 부분 점수 부여 가능",
                    "total_points": len(objective_questions)
                    + len(subjective_questions) * 5,
                    "passing_criteria": "총점의 60% 이상 획득 시 합격",
                },
            }

            summary_file = f"{summary_dir}/{filename}_test_summary_{timestamp}.json"
            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(test_summary_data, f, ensure_ascii=False, indent=2)
            print(f"📋 테스트 요약 저장: {summary_file}")
            return summary_file

        except Exception as e:
            print(f"⚠️ 테스트 요약 저장 실패: {e}")
            return None

    @staticmethod
    def _save_test_config(
        questions: List[Dict], source_file: str, timestamp: str
    ) -> str:
        """테스트 설정 파일 저장"""
        try:
            filename = os.path.splitext(os.path.basename(source_file))[0]
            config_dir = "data/outputs/test_configs"
            os.makedirs(config_dir, exist_ok=True)

            objective_questions = [q for q in questions if q.get("type") == "OBJECTIVE"]
            subjective_questions = [
                q for q in questions if q.get("type") == "SUBJECTIVE"
            ]

            test_config_data = {
                "test_metadata": {
                    "config_version": "1.0",
                    "test_id": f"auto_test_{timestamp}",
                    "source_document": source_file,
                    "generation_system": "SKIB-AI Question Generator",
                    "creation_timestamp": datetime.now().isoformat(),
                },
                "test_settings": {
                    "time_limit": {
                        "total_minutes": max(30, len(questions) * 2),
                        "warning_at_minutes": max(25, len(questions) * 2 - 5),
                        "automatic_submit": True,
                    },
                    "question_settings": {
                        "randomize_order": False,
                        "allow_review": True,
                        "show_progress": True,
                    },
                },
                "scoring_configuration": {
                    "objective_questions": {
                        "points_per_question": 1,
                        "negative_marking": False,
                    },
                    "subjective_questions": {
                        "points_per_question": 5,
                        "allow_partial_credit": True,
                        "manual_grading_required": True,
                    },
                    "total_points": len(objective_questions)
                    + len(subjective_questions) * 5,
                },
            }

            config_file = f"{config_dir}/{filename}_test_config_{timestamp}.json"
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(test_config_data, f, ensure_ascii=False, indent=2)
            print(f"⚙️ 테스트 설정 저장: {config_file}")
            return config_file

        except Exception as e:
            print(f"⚠️ 테스트 설정 저장 실패: {e}")
            return None
    
    @staticmethod
    def _analyze_content_complexity(
        keywords: List[str], main_topics: List[str], questions: List[Dict]
    ) -> str:
        """콘텐츠 복잡도 분석"""
        keywords_count = len(keywords)
        topics_count = len(main_topics)
        hard_questions = len(
            [q for q in questions if q.get("difficulty_level") == "HARD"]
        )

        if keywords_count > 10 and topics_count > 5 and hard_questions > 2:
            return "고급"
        elif keywords_count > 5 and topics_count > 3:
            return "중급"
        else:
            return "초급"

    @staticmethod
    def _extract_question_topics(questions: List[Dict]) -> List[str]:
        """문제에서 주요 주제 추출"""
        topics = []
        for q in questions[:3]:  # 상위 3개 문제만 분석
            question_text = q.get("question", "")
            # 간단한 키워드 추출
            if "프로세스" in question_text:
                topics.append("프로세스 관리")
            if "업무" in question_text:
                topics.append("업무 처리")
            if "계약" in question_text:
                topics.append("계약 관리")
            if "등록" in question_text:
                topics.append("등록 절차")

        return list(set(topics))[:3]  # 중복 제거 후 상위 3개 반환