"""
문제 생성 Agent
- GPT-4 Vision을 사용한 자동 문제 생성
- 테스트 요약 및 설정 파일 생성
- 문제 결과 저장 및 관리
"""

import json
import os
from datetime import datetime
from typing import Dict, List

from .tools.question_generator import QuestionGenerator


class QuestionGeneratorAgent:
    """
    문제 생성 전문 Agent

    주요 기능:
    - GPT-4 Vision을 사용한 자동 문제 생성
    - 객관식/주관식 문제 생성 및 관리
    - 테스트 요약 및 설정 파일 생성
    - 문제 결과 저장 및 관리
    """

    def __init__(self, collection_name: str = None):
        """
        QuestionGenerator 초기화

        Args:
            collection_name: 컬렉션명 (이미지 저장 경로 결정)
        """
        self.collection_name = collection_name

        # 이미지 저장 디렉토리 설정
        if collection_name:
            from utils.change_name import normalize_collection_name

            normalized_name = normalize_collection_name(collection_name)
            self.image_save_dir = f"data/images/{normalized_name}"
        else:
            self.image_save_dir = "data/images/unified"

        self.question_generator = QuestionGenerator(self.image_save_dir)

    def generate_questions_from_blocks(
        self,
        blocks: List[Dict],
        num_objective: int = 3,
        num_subjective: int = 3,
        source_file: str = "document.pdf",
        keywords: List[str] = None,
        main_topics: List[str] = None,
        summary: str = "",
        test_config: Dict = None,
        use_vectordb_search: bool = True,
    ) -> Dict:
        """
        블록들로부터 문제 생성 (vectorDB 검색 및 테스트 설정 활용)

        Args:
            blocks: 문서 블록들
            num_objective: 객관식 문제 수
            num_subjective: 주관식 문제 수
            source_file: 원본 파일명
            keywords: 키워드 목록
            main_topics: 주요 주제 목록
            summary: 문서 요약
            test_config: 테스트 설정 딕셔너리
            use_vectordb_search: vectorDB에서 관련 키워드 검색 활용 여부

        Returns:
            Dict: 문제 생성 결과
        """
        print("🤖 QuestionGeneratorAgent 시작")
        print(f"🎯 목표: 객관식 {num_objective}개, 주관식 {num_subjective}개")

        try:
            # 1. VectorDB에서 관련 키워드 검색 (선택적)
            enhanced_blocks = blocks
            if use_vectordb_search and keywords and self.collection_name:
                enhanced_blocks = self._enhance_blocks_with_vectordb_search(
                    blocks, keywords, main_topics
                )

            # 2. 테스트 설정에서 문제 수 조정
            if test_config:
                num_objective = test_config.get("num_objective", num_objective)
                num_subjective = test_config.get("num_subjective", num_subjective)
                print(
                    f"📊 테스트 설정 적용: 객관식 {num_objective}개, 주관식 {num_subjective}개"
                )

            # 3. 문제 생성 (향상된 블록과 테스트 설정 활용)
            questions_blocks = self.question_generator.generate_questions_for_blocks(
                blocks=enhanced_blocks,
                num_objective=num_objective,
                num_subjective=num_subjective,
                keywords=keywords,
                main_topics=main_topics,
                summary=summary,
                test_config=test_config,
            )

            # 2. 생성된 문제 추출
            all_questions = []
            for block in questions_blocks:
                if "questions" in block:
                    all_questions.extend(block["questions"])

            print(f"✅ 총 {len(all_questions)}개 문제 생성 완료")

            # 3. 결과 저장
            result = self._save_question_results(
                questions=all_questions,
                source_file=source_file,
                keywords=keywords or [],
                main_topics=main_topics or [],
                summary=summary,
            )

            return result

        except Exception as e:
            print(f"❌ 문제 생성 실패: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "questions": [],
                "files_created": [],
            }

    def _save_question_results(
        self,
        questions: List[Dict],
        source_file: str,
        keywords: List[str],
        main_topics: List[str],
        summary: str,
    ) -> Dict:
        """
        문제 생성 결과를 파일로 저장

        Args:
            questions: 생성된 문제 목록
            source_file: 원본 파일명
            keywords: 키워드 목록
            main_topics: 주요 주제 목록
            summary: 문서 요약

        Returns:
            Dict: 저장 결과 정보
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.splitext(os.path.basename(source_file))[0]
        files_created = []

        # 1. 생성된 문제 파일 저장
        questions_dir = "data/outputs/generated_questions"
        os.makedirs(questions_dir, exist_ok=True)

        questions_data = {
            "test_info": {
                "source_file": source_file,
                "collection_name": self.collection_name,
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
        summary_file = self._save_test_summary(
            questions, source_file, keywords, main_topics, summary, timestamp
        )
        if summary_file:
            files_created.append(summary_file)

        # 3. 테스트 config 파일 생성
        config_file = self._save_test_config(questions, source_file, timestamp)
        if config_file:
            files_created.append(config_file)

        return {
            "status": "completed",
            "questions": questions,
            "total_questions": len(questions),
            "objective_count": len(
                [q for q in questions if q.get("type") == "OBJECTIVE"]
            ),
            "subjective_count": len(
                [q for q in questions if q.get("type") == "SUBJECTIVE"]
            ),
            "files_created": files_created,
            "collection_name": self.collection_name,
        }

    def _save_test_summary(
        self,
        questions: List[Dict],
        source_file: str,
        keywords: List[str],
        main_topics: List[str],
        summary: str,
        timestamp: str,
    ) -> str:
        """
        테스트 요약 파일 저장

        Args:
            questions: 생성된 문제 목록
            source_file: 원본 파일명
            keywords: 키워드 목록
            main_topics: 주요 주제 목록
            summary: 문서 요약
            timestamp: 타임스탬프

        Returns:
            str: 저장된 파일 경로 (실패 시 None)
        """
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
                    "content_complexity": self._analyze_content_complexity(
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
                            "focus_areas": self._extract_question_topics(
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
                            "focus_areas": self._extract_question_topics(
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

    def _save_test_config(
        self, questions: List[Dict], source_file: str, timestamp: str
    ) -> str:
        """
        테스트 설정 파일 저장

        Args:
            questions: 생성된 문제 목록
            source_file: 원본 파일명
            timestamp: 타임스탬프

        Returns:
            str: 저장된 파일 경로 (실패 시 None)
        """
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

    def _analyze_content_complexity(
        self, keywords: List[str], main_topics: List[str], questions: List[Dict]
    ) -> str:
        """
        콘텐츠 복잡도 분석

        Args:
            keywords: 키워드 목록
            main_topics: 주요 주제 목록
            questions: 생성된 문제 목록

        Returns:
            str: 복잡도 등급 ("초급", "중급", "고급")
        """
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

    def _extract_question_topics(self, questions: List[Dict]) -> List[str]:
        """
        문제에서 주요 주제 추출

        Args:
            questions: 문제 목록

        Returns:
            List[str]: 추출된 주제 목록 (최대 3개)
        """
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

    def _enhance_blocks_with_vectordb_search(
        self, blocks: List[Dict], keywords: List[str], main_topics: List[str]
    ) -> List[Dict]:
        """
        VectorDB 검색을 통해 블록을 향상시키는 메서드

        Args:
            blocks: 원본 블록들
            keywords: 검색할 키워드들
            main_topics: 주요 주제들

        Returns:
            List[Dict]: 향상된 블록들 (관련 내용 추가)
        """
        try:
            print("🔍 VectorDB에서 관련 키워드 검색 중...")

            # ChromaDB 검색 시도
            try:
                from db.vectorDB.chromaDB.search import search_documents

                enhanced_blocks = blocks.copy()
                related_contents = []

                # 상위 키워드들로 검색
                top_keywords = keywords[:5]  # 상위 5개 키워드만 사용
                for keyword in top_keywords:
                    try:
                        search_results = search_documents(
                            query=keyword,
                            collection_name=self.collection_name,
                            n_results=3,
                        )

                        if search_results and "documents" in search_results:
                            for doc in search_results["documents"][
                                0
                            ]:  # 첫 번째 검색 결과 배치
                                if doc not in related_contents:
                                    related_contents.append(doc)

                    except Exception as e:
                        print(f"  ⚠️ 키워드 '{keyword}' 검색 실패: {e}")
                        continue

                # 검색된 관련 내용을 블록에 추가
                if related_contents:
                    print(f"  ✅ {len(related_contents)}개 관련 내용 발견")

                    # 관련 내용을 새로운 텍스트 블록으로 추가
                    for i, content in enumerate(
                        related_contents[:3]
                    ):  # 최대 3개만 추가
                        related_block = {
                            "type": "paragraph",
                            "content": f"[관련 내용 {i+1}] {content}",
                            "metadata": {
                                "source": "vectordb_search",
                                "search_keyword": (
                                    keywords[i % len(keywords)]
                                    if keywords
                                    else "unknown"
                                ),
                                "page": "vectordb",
                            },
                        }
                        enhanced_blocks.append(related_block)

                return enhanced_blocks

            except ImportError:
                print("  ⚠️ ChromaDB 모듈을 찾을 수 없습니다. 원본 블록 사용")
                return blocks

        except Exception as e:
            print(f"  ❌ VectorDB 검색 실패: {e}")
            return blocks


# 편의 함수
def generate_questions_from_document(
    blocks: List[Dict],
    collection_name: str = None,
    num_objective: int = 3,
    num_subjective: int = 3,
    source_file: str = "document.pdf",
    keywords: List[str] = None,
    main_topics: List[str] = None,
    summary: str = "",
) -> Dict:
    """
    문서 블록들로부터 문제 생성 편의 함수

    Args:
        blocks: 문서 블록들
        collection_name: 컬렉션명
        num_objective: 객관식 문제 수
        num_subjective: 주관식 문제 수
        source_file: 원본 파일명
        keywords: 키워드 목록
        main_topics: 주요 주제 목록
        summary: 문서 요약

    Returns:
        Dict: 문제 생성 결과
    """
    agent = QuestionGeneratorAgent(collection_name)
    return agent.generate_questions_from_blocks(
        blocks,
        num_objective,
        num_subjective,
        source_file,
        keywords,
        main_topics,
        summary,
    )


"""
문제 생성 Agent
- GPT-4 Vision을 사용한 자동 문제 생성
- 테스트 요약 및 설정 파일 생성
- 문제 결과 저장 및 관리
"""

import json
import os
from datetime import datetime
from typing import Dict, List

from .tools.question_generator import QuestionGenerator


class QuestionGeneratorAgent:
    """문제 생성 전문 Agent"""

    def __init__(self, collection_name: str = None):
        self.collection_name = collection_name
        # 이미지 저장 디렉토리 설정
        if collection_name:
            from utils.naming import filename_to_collection

            normalized_name = filename_to_collection(collection_name)
            self.image_save_dir = f"data/images/{normalized_name}"
        else:
            self.image_save_dir = "data/images/unified"
        self.question_generator = QuestionGenerator(self.image_save_dir)

    def generate_questions_from_blocks(
        self,
        blocks: List[Dict],
        num_objective: int = 3,
        num_subjective: int = 3,
        source_file: str = "document.pdf",
        keywords: List[str] = None,
        main_topics: List[str] = None,
        summary: str = "",
    ) -> Dict:
        """
        블록들로부터 문제 생성

        Args:
            blocks: 문서 블록들
            num_objective: 객관식 문제 수
            num_subjective: 주관식 문제 수
            source_file: 원본 파일명
            keywords: 키워드 목록
            main_topics: 주요 주제 목록
            summary: 문서 요약

        Returns:
            Dict: 문제 생성 결과
        """
        print("🤖 QuestionGeneratorAgent 시작")
        print(f"🎯 목표: 객관식 {num_objective}개, 주관식 {num_subjective}개")

        try:
            # 1. 문제 생성
            questions_blocks = self.question_generator.generate_questions_for_blocks(
                blocks, num_objective, num_subjective
            )

            # 2. 생성된 문제 추출
            all_questions = []
            for block in questions_blocks:
                if "questions" in block:
                    all_questions.extend(block["questions"])

            print(f"✅ 총 {len(all_questions)}개 문제 생성 완료")

            # 3. 결과 저장
            result = self._save_question_results(
                questions=all_questions,
                source_file=source_file,
                keywords=keywords or [],
                main_topics=main_topics or [],
                summary=summary,
            )

            return result

        except Exception as e:
            print(f"❌ 문제 생성 실패: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "questions": [],
                "files_created": [],
            }

    def _save_question_results(
        self,
        questions: List[Dict],
        source_file: str,
        keywords: List[str],
        main_topics: List[str],
        summary: str,
    ) -> Dict:
        """문제 생성 결과 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.splitext(os.path.basename(source_file))[0]
        files_created = []

        # 1. 생성된 문제 파일 저장
        questions_dir = "data/outputs/generated_questions"
        os.makedirs(questions_dir, exist_ok=True)

        questions_data = {
            "test_info": {
                "source_file": source_file,
                "collection_name": self.collection_name,
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
        summary_file = self._save_test_summary(
            questions, source_file, keywords, main_topics, summary, timestamp
        )
        if summary_file:
            files_created.append(summary_file)

        # 3. 테스트 config 파일 생성
        config_file = self._save_test_config(questions, source_file, timestamp)
        if config_file:
            files_created.append(config_file)

        return {
            "status": "completed",
            "questions": questions,
            "total_questions": len(questions),
            "objective_count": len(
                [q for q in questions if q.get("type") == "OBJECTIVE"]
            ),
            "subjective_count": len(
                [q for q in questions if q.get("type") == "SUBJECTIVE"]
            ),
            "files_created": files_created,
            "collection_name": self.collection_name,
        }

    def _save_test_summary(
        self,
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
                    "content_complexity": self._analyze_content_complexity(
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
                            "focus_areas": self._extract_question_topics(
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
                            "focus_areas": self._extract_question_topics(
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

    def _save_test_config(
        self, questions: List[Dict], source_file: str, timestamp: str
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

    def _analyze_content_complexity(
        self, keywords: List[str], main_topics: List[str], questions: List[Dict]
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

    def _extract_question_topics(self, questions: List[Dict]) -> List[str]:
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


# 편의 함수
def generate_questions_from_document(
    blocks: List[Dict],
    collection_name: str = None,
    num_objective: int = 3,
    num_subjective: int = 3,
    source_file: str = "document.pdf",
    keywords: List[str] = None,
    main_topics: List[str] = None,
    summary: str = "",
) -> Dict:
    """
    문서 블록들로부터 문제 생성 편의 함수

    Args:
        blocks: 문서 블록들
        collection_name: 컬렉션명
        num_objective: 객관식 문제 수
        num_subjective: 주관식 문제 수
        source_file: 원본 파일명
        keywords: 키워드 목록
        main_topics: 주요 주제 목록
        summary: 문서 요약

    Returns:
        Dict: 문제 생성 결과
    """
    agent = QuestionGeneratorAgent(collection_name)
    return agent.generate_questions_from_blocks(
        blocks,
        num_objective,
        num_subjective,
        source_file,
        keywords,
        main_topics,
        summary,
    )
