"""
문서 분석 Agent
- 문서 구조 파싱
- 질문 생성
- 키워드 추출
- 문서 요약
"""

from typing import Dict, List

from .state import DocumentAnalyzerState, create_document_analyzer_state
from .tools.text_analyzer import TextAnalyzer
from .tools.unified_parser import parse_pdf_unified


class DocumentAnalyzerAgent:
    """문서 분석 전문 Agent"""

    """
    문서 분석 전문 Agent
    주요 기능:
    - PDF 문서의 구조 파싱 (텍스트, 이미지, 표)
    - 키워드 추출 및 문서 요약
    - ChromaDB 자동 업로드
    - 분석 결과 저장 및 관리
    """

    def __init__(self, collection_name: str = None, auto_upload_chromadb: bool = True):
        """
        DocumentAnalyzer 초기화

        Args:
            collection_name: ChromaDB 컬렉션명
            auto_upload_chromadb: ChromaDB 자동 업로드 활성화 여부
        """
        self.collection_name = collection_name
        self.auto_upload_chromadb = auto_upload_chromadb

        # 이미지 저장 디렉토리 설정
        if collection_name:
            from utils.naming import filename_to_collection

            normalized_name = filename_to_collection(collection_name)
            self.image_save_dir = f"data/images/{normalized_name}"
        else:
            self.image_save_dir = "data/images/unified"

        self.text_analyzer = TextAnalyzer()

    def analyze_document(
        self, pdf_path: str, extract_keywords: bool = True
    ) -> DocumentAnalyzerState:
        """
        문서 종합 분석


        Args:
            pdf_path: PDF 파일 경로
            extract_keywords: 키워드 추출 여부


        Returns:
            DocumentAnalyzerState: 분석 결과
        """
        state = create_document_analyzer_state(pdf_path, self.collection_name)

        try:
            # 1. 문서 구조 파싱
            print("📄 1단계: 문서 구조 파싱")
            blocks = parse_pdf_unified(
                pdf_path, self.collection_name, generate_questions=False
            )
            state["blocks"] = blocks
            state["total_blocks"] = len(blocks)

            # 블록 타입별 통계
            state["text_blocks"] = len(
                [
                    b
                    for b in blocks
                    if b.get("type") in ["paragraph", "section", "heading"]
                ]
            )
            state["table_blocks"] = len([b for b in blocks if b.get("type") == "table"])
            state["image_blocks"] = len([b for b in blocks if b.get("type") == "image"])

            # 2. 텍스트 분석 및 키워드 추출 (선택적)
            if extract_keywords:
                print("\n📝 2단계: 텍스트 분석 및 키워드 추출")
                # keyword_summary.py 함수 사용 (document_analyzer로 이동)
                from .tools.keyword_summary import extract_keywords_and_summary

                try:
                    analysis_result = extract_keywords_and_summary(
                        blocks, pdf_path.split("/")[-1]
                    )
                    content_analysis = analysis_result.get("content_analysis", {})

                    state["keywords"] = content_analysis.get("key_concepts", [])
                    state["summary"] = content_analysis.get("summary", "")
                    state["main_topics"] = content_analysis.get("main_topics", [])

                    print(f"✅ 키워드 추출 완료:")
                    print(f"   - 키워드: {len(state['keywords'])}개")
                    print(f"   - 주제: {len(state['main_topics'])}개")
                    print(f"   - 요약: {state['summary'][:50]}...")

                except Exception as e:
                    print(f"⚠️ 키워드 추출 실패: {e}")
                    state["keywords"] = []
                    state["summary"] = f"키워드 추출 실패: {str(e)}"
                    state["main_topics"] = []

            state["processing_status"] = "completed"
            state["error_message"] = None

            # 3. ChromaDB 자동 업로드 (선택적)
            if self.auto_upload_chromadb and self.collection_name:
                print("\n📤 3단계: ChromaDB 자동 업로드")
                uploaded_count = self._upload_to_chromadb(blocks, pdf_path)
                state["chromadb_uploaded"] = uploaded_count > 0
                state["chromadb_upload_count"] = uploaded_count
                if uploaded_count > 0:
                    print(f"✅ ChromaDB 업로드 완료: {uploaded_count}개 청크")
                else:
                    print("⚠️ ChromaDB 업로드 실패")
            else:
                state["chromadb_uploaded"] = False
                state["chromadb_upload_count"] = 0

            # 4. 결과 저장
            self._save_results(state, pdf_path, extract_keywords)

        except Exception as e:
            state["processing_status"] = "failed"
            state["error_message"] = str(e)
            print(f"❌ 문서 분석 실패: {e}")

        return state

    def parse_structure_only(self, pdf_path: str) -> List[Dict]:
        """구조 파싱만 수행"""
        return parse_pdf_unified(
            pdf_path, self.collection_name, generate_questions=False
        )

        """
        문서 구조 파싱만 수행 (키워드 추출 없이)

        Args:
            pdf_path: PDF 파일 경로

        Returns:
            List[Dict]: 구조화된 블록들
        """
        return parse_pdf_unified(
            pdf_path, self.collection_name, generate_questions=False
        )

    def analyze_text_only(self, text: str, collection_name: str = None) -> Dict:
        """텍스트 분석만 수행"""
        return self.text_analyzer.analyze_text(
            text, collection_name or self.collection_name or "unknown"
        )

        """
        텍스트 분석만 수행 (구조 파싱 없이)

        Args:
            text: 분석할 텍스트
            collection_name: 컬렉션명 (옵션)

        Returns:
            Dict: 텍스트 분석 결과
        """
        return self.text_analyzer.analyze_text(
            text, collection_name or self.collection_name or "unknown"
        )

    def _extract_all_text(self, blocks: List[Dict]) -> str:
        """
        블록들에서 모든 텍스트 추출

        Args:
            blocks: 문서 블록들

        Returns:
            str: 추출된 전체 텍스트
        """
        text_parts = []

        for block in blocks:
            block_type = block.get("type", "")
            content = block.get("content", "")

            if block_type in ["paragraph", "heading", "section"] and content:
                text_parts.append(str(content))
            elif block_type == "table" and isinstance(content, dict):
                # 표 내용을 텍스트로 변환
                table_text = self._table_to_text(content)
                if table_text:
                    text_parts.append(table_text)

        return "\n".join(text_parts)

    def _save_results(
        self, state: DocumentAnalyzerState, pdf_path: str, extract_keywords: bool
    ):
        """
        분석 결과를 구분된 디렉토리에 저장

        Args:
            state: 분석 상태
            pdf_path: PDF 파일 경로
            extract_keywords: 키워드 추출 여부
        """
        import json
        import os
        from datetime import datetime

        filename = os.path.basename(pdf_path).replace(".pdf", "")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 키워드/요약 결과 저장

        # 키워드/요약 결과 저장 (collection 명 기반 디렉토리)
        if extract_keywords and (state.get("keywords") or state.get("summary")):
            # Collection 명 기반 디렉토리 구조
            collection_dir = self.collection_name or "default"
            keywords_dir = f"data/outputs/keywords_summary/{collection_dir}"
            os.makedirs(keywords_dir, exist_ok=True)

            keywords_data = {
                "document_info": {
                    "source_file": os.path.basename(pdf_path),
                    "collection_name": self.collection_name,
                    "processing_date": datetime.now().isoformat(),
                    "analysis_type": "keywords_and_summary",
                    "analysis_type": "keywords_and_summary",
                },
                "content_analysis": {
                    "keywords": state.get("keywords", []),
                    "main_topics": state.get("main_topics", []),
                    "summary": state.get("summary", ""),
                    "keywords_count": len(state.get("keywords", [])),
                    "topics_count": len(state.get("main_topics", [])),
                },
                "document_stats": {
                    "total_blocks": state.get("total_blocks", 0),
                    "text_blocks": state.get("text_blocks", 0),
                    "table_blocks": state.get("table_blocks", 0),
                    "image_blocks": state.get("image_blocks", 0),
                },
            }

            keywords_file = (
                f"{keywords_dir}/{filename}_keywords_summary_{timestamp}.json"
            )
            with open(keywords_file, "w", encoding="utf-8") as f:
                json.dump(keywords_data, f, ensure_ascii=False, indent=2)
            print(f"💾 키워드/요약 저장: {keywords_file}")

        # 전체 분석 결과 저장 (블록 포함) - question_generation을 위해
        analysis_results_dir = (
            f"data/outputs/document_analysis/{self.collection_name or 'default'}"
        )
        os.makedirs(analysis_results_dir, exist_ok=True)

        analysis_result_data = {
            "document_info": {
                "source_file": os.path.basename(pdf_path),
                "collection_name": self.collection_name,
                "processing_date": datetime.now().isoformat(),
                "analysis_type": "full_analysis",
            },
            "analysis_result": state,
            "pipeline_info": {
                "pipeline_type": "document_analysis",
                "pdf_path": pdf_path,
                "collection_name": self.collection_name,
                "extract_keywords": extract_keywords,
                "processing_time": 0,  # 실제 시간은 pipeline에서 계산
                "timestamp": datetime.now().isoformat(),
            },
        }

        analysis_file = (
            f"{analysis_results_dir}/{filename}_analysis_result_{timestamp}.json"
        )
        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis_result_data, f, ensure_ascii=False, indent=2)
        print(f"💾 전체 분석 결과 저장: {analysis_file}")

    def _table_to_text(self, table_data: Dict) -> str:
        """
        표 데이터를 텍스트로 변환

        Args:
            table_data: 표 데이터

        Returns:
            str: 변환된 텍스트
        """
        if not isinstance(table_data, dict) or "data" not in table_data:
            return ""

        headers = table_data.get("headers", [])
        data = table_data.get("data", [])

        text_parts = []
        if headers:
            text_parts.append(" ".join(str(h) for h in headers))

        for row in data:
            text_parts.append(" ".join(str(cell) for cell in row))

        return " ".join(text_parts)

    def _save_test_summary(
        self,
        state: DocumentAnalyzerState,
        pdf_path: str,
        questions: List[Dict],
        timestamp: str,
    ):
        """테스트 요약 파일 저장"""
        import json
        import os
        from datetime import datetime

        filename = os.path.basename(pdf_path).replace(".pdf", "")
        summary_dir = "data/outputs/test_summaries"
        os.makedirs(summary_dir, exist_ok=True)

        # 문제 난이도별 분석
        objective_questions = [q for q in questions if q.get("type") == "OBJECTIVE"]
        subjective_questions = [q for q in questions if q.get("type") == "SUBJECTIVE"]

        # 주요 키워드와 주제 분석
        keywords = state.get("keywords", [])
        main_topics = state.get("main_topics", [])

        # 테스트 요약 데이터 구성
        test_summary_data = {
            "test_overview": {
                "title": f"{filename} - 자동 생성 테스트",
                "description": f"'{filename}' 문서를 기반으로 AI가 자동 생성한 평가 테스트입니다.",
                "source_document": os.path.basename(pdf_path),
                "creation_date": datetime.now().isoformat(),
                "test_type": "종합 평가",
                "estimated_duration": "30-45분",
            },
            "content_analysis": {
                "document_summary": (
                    state.get("summary", "")[:300] + "..."
                    if len(state.get("summary", "")) > 300
                    else state.get("summary", "")
                ),
                "key_concepts": keywords[:10],  # 상위 10개 키워드
                "main_topics": main_topics[:5],  # 상위 5개 주제
                "content_complexity": self._analyze_content_complexity(
                    state, questions
                ),
            },
            "test_structure": {
                "total_questions": len(questions),
                "question_breakdown": {
                    "objective": {
                        "count": len(objective_questions),
                        "percentage": (
                            round(len(objective_questions) / len(questions) * 100, 1)
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
                            round(len(subjective_questions) / len(questions) * 100, 1)
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
            "assessment_guidelines": {
                "objective_scoring": "각 객관식 문항당 1점, 정답/오답으로 채점",
                "subjective_scoring": "문항별 배점에 따라 부분 점수 부여 가능",
                "total_points": len(objective_questions)
                + len(subjective_questions) * 5,  # 객관식 1점, 주관식 5점
                "passing_criteria": "총점의 60% 이상 획득 시 합격",
                "special_instructions": [
                    "주관식 문항은 키워드 포함 여부와 논리적 구성을 중점 평가",
                    "문서의 핵심 개념 이해도를 종합적으로 판단",
                    "실무 적용 가능성을 고려한 평가 권장",
                ],
            },
            "usage_recommendations": {
                "target_audience": "문서 내용 학습자 및 관련 업무 담당자",
                "prerequisite_knowledge": "기본적인 문서 내용 이해",
                "application_scenarios": [
                    "학습 완료 후 이해도 점검",
                    "업무 숙련도 평가",
                    "교육 프로그램 효과 측정",
                ],
                "follow_up_actions": [
                    "오답 문항에 대한 추가 학습",
                    "약점 영역 집중 보완",
                    "실무 적용 연습",
                ],
            },
        }

        summary_file = f"{summary_dir}/{filename}_test_summary_{timestamp}.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(test_summary_data, f, ensure_ascii=False, indent=2)
        print(f"📋 테스트 요약 저장: {summary_file}")

    def _save_test_config(
        self,
        state: DocumentAnalyzerState,
        pdf_path: str,
        questions: List[Dict],
        timestamp: str,
    ):
        """테스트 설정 파일 저장"""
        import json
        import os
        from datetime import datetime

        filename = os.path.basename(pdf_path).replace(".pdf", "")
        config_dir = "data/outputs/test_configs"
        os.makedirs(config_dir, exist_ok=True)

        objective_questions = [q for q in questions if q.get("type") == "OBJECTIVE"]
        subjective_questions = [q for q in questions if q.get("type") == "SUBJECTIVE"]

        # 테스트 설정 데이터 구성
        test_config_data = {
            "test_metadata": {
                "config_version": "1.0",
                "test_id": f"auto_test_{timestamp}",
                "source_document": os.path.basename(pdf_path),
                "generation_system": "SKIB-AI Document Analyzer",
                "creation_timestamp": datetime.now().isoformat(),
            },
            "test_settings": {
                "time_limit": {
                    "total_minutes": max(
                        30, len(questions) * 2
                    ),  # 최소 30분, 문항당 2분
                    "warning_at_minutes": max(25, len(questions) * 2 - 5),
                    "automatic_submit": True,
                },
                "question_settings": {
                    "randomize_order": False,
                    "allow_review": True,
                    "show_progress": True,
                    "one_question_per_page": False,
                },
                "submission_settings": {
                    "allow_multiple_attempts": False,
                    "save_progress": True,
                    "require_all_answers": False,
                },
            },
            "scoring_configuration": {
                "objective_questions": {
                    "points_per_question": 1,
                    "negative_marking": False,
                    "partial_credit": False,
                },
                "subjective_questions": {
                    "points_per_question": 5,
                    "allow_partial_credit": True,
                    "manual_grading_required": True,
                    "grading_rubric": "키워드 기반 + 논리적 구성 평가",
                },
                "total_points": len(objective_questions)
                + len(subjective_questions) * 5,
                "grade_scale": {
                    "A": {"min_percentage": 90, "description": "우수"},
                    "B": {"min_percentage": 80, "description": "양호"},
                    "C": {"min_percentage": 70, "description": "보통"},
                    "D": {"min_percentage": 60, "description": "미흡"},
                    "F": {"min_percentage": 0, "description": "불합격"},
                },
            },
            "question_configuration": {
                "total_questions": len(questions),
                "question_types": {
                    "objective": {
                        "count": len(objective_questions),
                        "format": "multiple_choice",
                        "options_per_question": 4,
                        "scoring_method": "correct_answer_only",
                    },
                    "subjective": {
                        "count": len(subjective_questions),
                        "format": "essay",
                        "max_characters": 1000,
                        "scoring_method": "rubric_based",
                    },
                },
                "difficulty_levels": {
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
            "grading_criteria": {
                "objective_grading": {
                    "method": "automatic",
                    "correct_answer_points": 1,
                    "incorrect_answer_points": 0,
                },
                "subjective_grading": {
                    "method": "manual_with_ai_assistance",
                    "evaluation_criteria": [
                        {
                            "criterion": "내용 정확성",
                            "weight": 40,
                            "description": "답변 내용의 사실적 정확성",
                        },
                        {
                            "criterion": "핵심 키워드 포함",
                            "weight": 30,
                            "description": "문제와 관련된 핵심 용어 사용",
                        },
                        {
                            "criterion": "논리적 구성",
                            "weight": 20,
                            "description": "답변의 논리적 흐름과 구조",
                        },
                        {
                            "criterion": "완성도",
                            "weight": 10,
                            "description": "답변의 완전성과 충실도",
                        },
                    ],
                },
            },
            "accessibility_settings": {
                "font_size_adjustable": True,
                "high_contrast_mode": True,
                "screen_reader_compatible": True,
                "keyboard_navigation": True,
            },
            "security_settings": {
                "prevent_copy_paste": False,
                "disable_print_screen": False,
                "session_timeout_minutes": 120,
                "ip_restriction": False,
            },
        }

        config_file = f"{config_dir}/{filename}_test_config_{timestamp}.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(test_config_data, f, ensure_ascii=False, indent=2)
        print(f"⚙️ 테스트 설정 저장: {config_file}")

    def _analyze_content_complexity(
        self, state: DocumentAnalyzerState, questions: List[Dict]
    ) -> str:
        """콘텐츠 복잡도 분석"""
        keywords_count = len(state.get("keywords", []))
        topics_count = len(state.get("main_topics", []))
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
            # 간단한 키워드 추출 (실제로는 더 정교한 방법 사용 가능)
            if "프로세스" in question_text:
                topics.append("프로세스 관리")
            if "업무" in question_text:
                topics.append("업무 처리")
            if "계약" in question_text:
                topics.append("계약 관리")
            if "등록" in question_text:
                topics.append("등록 절차")

        return list(set(topics))[:3]  # 중복 제거 후 상위 3개 반환

    def _upload_to_chromadb(self, blocks: List[Dict], pdf_path: str) -> int:
        """
        블록들을 ChromaDB에 업로드

        Args:
            blocks: 업로드할 블록들
            pdf_path: PDF 파일 경로

        Returns:
            int: 업로드된 블록 수
        """
        try:
            import os

            from db.vectorDB.chromaDB import upload_documents

            source_file = os.path.basename(pdf_path)
            uploaded_count = upload_documents(blocks, self.collection_name, source_file)
            return uploaded_count

        except ImportError:
            print(
                "⚠️ ChromaDB 모듈을 찾을 수 없습니다. ChromaDB가 설치되어 있는지 확인하세요."
            )
            return 0
        except Exception as e:
            print(f"❌ ChromaDB 업로드 실패: {e}")
            return 0


# 편의 함수들
def analyze_document_complete(
    pdf_path: str,
    collection_name: str = None,
    extract_keywords: bool = True,
    auto_upload_chromadb: bool = True,
) -> DocumentAnalyzerState:
    """
    문서 종합 분석 편의 함수 (ChromaDB 자동 업로드 포함)

    Args:
        pdf_path: PDF 파일 경로
        collection_name: 컬렉션명
        extract_keywords: 키워드 추출 여부
        auto_upload_chromadb: ChromaDB 자동 업로드 여부

    Returns:
        DocumentAnalyzerState: 분석 결과
    """
    agent = DocumentAnalyzerAgent(collection_name, auto_upload_chromadb)
    return agent.analyze_document(pdf_path, extract_keywords)


def parse_document_structure(pdf_path: str, collection_name: str = None) -> List[Dict]:
    """
    문서 구조 파싱 편의 함수

    Args:
        pdf_path: PDF 파일 경로
        collection_name: 컬렉션명

    Returns:
        List[Dict]: 구조화된 블록들
    """
    return parse_pdf_unified(pdf_path, collection_name, generate_questions=False)
