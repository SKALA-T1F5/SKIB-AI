"""
문제 생성 Agent
- GPT-4 Vision을 사용한 자동 문제 생성
- 테스트 요약 및 설정 파일 생성
- 문제 결과 저장 및 관리
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from .tools.question_generator import QuestionGenerator
from .tools.result_saver import ResultSaver
from .tools.test_plan_handler import TestPlanHandler
from .tools.vector_search import VectorSearchHandler

logger = logging.getLogger(__name__)


class QuestionGeneratorAgent:
    """문제 생성 전문 Agent"""

    def __init__(self, collection_name: str | None = None):
        self.collection_name = collection_name
        # 이미지 저장 디렉토리 설정
        if collection_name is None:
            from utils.naming import filename_to_collection

            normalized_name = filename_to_collection(collection_name)
            self.image_save_dir = f"data/images/{normalized_name}"
        else:
            self.image_save_dir = "data/images/unified"
        self.question_generator = QuestionGenerator(self.image_save_dir)

        # Tools 초기화
        self.test_plan_handler = TestPlanHandler()
        self.vector_search_handler = VectorSearchHandler()
        self.result_saver = ResultSaver()

    def generate_enhanced_questions_from_test_plans(
        self,
        total_test_plan_path: str | None = None,
        document_test_plan_path: str | None = None,
        total_test_plan_data: Dict | None = None,
        document_test_plan_data: Dict | None = None,
    ) -> Dict[str, Any]:
        """
        테스트 계획을 기반으로 향상된 문제 생성

        Args:
            total_test_plan_path: 전체 테스트 계획 파일 경로 (선택사항)
            document_test_plan_path: 문서별 테스트 계획 파일 경로 (선택사항)
            total_test_plan_data: 전체 테스트 계획 데이터 딕셔너리 (선택사항)
            document_test_plan_data: 문서별 테스트 계획 데이터 딕셔너리 (선택사항)
        Returns:
            Dict: 문제 생성 결과
        """
        logger.info("🚀 향상된 문제 생성기 시작")

        # 1. Test Plan 로드 (우선순위: 데이터 > 경로 > 자동 검색)
        total_plan = None
        document_plan = None

        if total_test_plan_data and document_test_plan_data:
            # 직접 딕셔너리 데이터 사용
            total_plan = total_test_plan_data
            document_plan = document_test_plan_data
            logger.info("📋 Test Plan 데이터를 직접 딕셔너리로 받음")
        elif total_test_plan_path and document_test_plan_path:
            # 지정된 경로에서 로드 -> Local Test용
            total_plan, document_plan = self.test_plan_handler.load_specific_test_plans(
                total_test_plan_path, document_test_plan_path
            )
            if not total_plan or not document_plan:
                return {"status": "failed", "error": "지정된 Test plan 파일 로드 실패"}
        else:
            # 자동으로 최신 파일 찾기
            total_plan, document_plan = self.test_plan_handler.load_latest_test_plans()
            if not total_plan or not document_plan:
                return {
                    "status": "failed",
                    "error": "Test plan 파일을 찾을 수 없습니다.",
                }

        all_generated_questions = []
        generation_summary = {
            "total_documents": len(document_plan.get("document_plans", [])),
            "documents_processed": [],
            "total_questions_generated": 0,
            "basic_questions": 0,
            "extra_questions": 0,
        }

        # 전체 테스트 계획에서 난이도 추출
        difficulty = total_plan.get("test_plan", {}).get("difficulty_level", "NORMAL")

        # 2. 각 문서별로 문제 생성
        for doc_plan in document_plan.get("document_plans", []):
            document_name = doc_plan.get("document_name", "Unknown")
            document_id = doc_plan.get("document_id", None)
            keywords = doc_plan.get("keywords", [])
            recommended = doc_plan.get("recommended_questions", {})

            logger.info(f"\n📄 문서 처리: {document_name}")
            logger.info(f"🔑 키워드: {', '.join(keywords)}")
            logger.info(
                f"📊 추천 문제수: 객관식 {recommended.get('objective', 0)}개, 주관식 {recommended.get('subjective', 0)}개"
            )
            logger.info(f"🎯 난이도: {difficulty}")

            # VectorDB에서 키워드 관련 콘텐츠 검색 (문서명을 자동으로 collection명으로 변환)
            if document_name:
                related_content = (
                    self.vector_search_handler.search_keywords_in_collection(
                        keywords, document_name
                    )
                )
            else:
                # 문서명이 없는 경우 fallback 컬렉션들에서 검색
                related_content = (
                    self.vector_search_handler.search_with_fallback_collections(
                        keywords=keywords, primary_document_name=""
                    )
                )

            doc_questions = []

            # 3. 기본 문제 생성 (추천 문제수)
            basic_questions = self._generate_questions_with_context(
                keywords=keywords,
                related_content=related_content,
                document_name=document_name,
                document_id=document_id,
                num_objective=recommended.get("objective", 0),
                num_subjective=recommended.get("subjective", 0),
                question_type="BASIC",
                difficulty=difficulty,
                total_test_plan=total_plan,
                document_test_plan=doc_plan,
            )
            doc_questions.extend(basic_questions)

            # 4. 여분 문제 생성 (키워드별 2문제씩)
            extra_objective, extra_subjective = (
                self.test_plan_handler.calculate_extra_questions(keywords)
            )

            if extra_objective > 0 or extra_subjective > 0:
                logger.info(
                    f"  🎯 여분 문제 생성: 객관식 {extra_objective}개, 주관식 {extra_subjective}개"
                )

                extra_questions = self._generate_questions_with_context(
                    keywords=keywords,
                    related_content=related_content,
                    document_name=document_name,
                    document_id=document_id,
                    num_objective=extra_objective,
                    num_subjective=extra_subjective,
                    question_type="EXTRA",
                    difficulty=difficulty,
                    total_test_plan=total_plan,
                    document_test_plan=doc_plan,
                )
                doc_questions.extend(extra_questions)

            # 결과 요약
            basic_count = len(basic_questions)
            extra_count = len(doc_questions) - basic_count

            generation_summary["documents_processed"].append(
                {
                    "document_name": document_name,
                    "keywords": keywords,
                    "basic_questions": basic_count,
                    "extra_questions": extra_count,
                    "total_questions": len(doc_questions),
                }
            )

            generation_summary["basic_questions"] += basic_count
            generation_summary["extra_questions"] += extra_count

            all_generated_questions.extend(doc_questions)

            logger.info(
                f"  ✅ '{document_name}' 문제 생성 완료: 기본 {basic_count}개 + 여분 {extra_count}개 = 총 {len(doc_questions)}개"
            )

        generation_summary["total_questions_generated"] = len(all_generated_questions)

        # 5. 결과 저장
        result = self.result_saver.save_enhanced_questions(
            questions=all_generated_questions,
            summary=generation_summary,
            total_plan=total_plan,
            document_plan=document_plan,
        )

        return result

    def _generate_questions_with_context(
        self,
        keywords: List[str],
        related_content: List[Dict],
        document_name: str,
        document_id: int,
        num_objective: int,
        num_subjective: int,
        question_type: str = "BASIC",
        difficulty: str = "NORMAL",
        total_test_plan: Dict | None = None,
        document_test_plan: Dict | None = None,
    ) -> List[Dict]:
        """콘텍스트를 활용한 문제 생성 (기존 QuestionGenerator 활용)"""
        if num_objective == 0 and num_subjective == 0:
            return []

        try:
            # 관련 콘텐츠를 블록 형태로 변환
            context_blocks = self._convert_content_to_blocks(related_content, keywords)

            # TODO: ChromaDB 연결 되면 이거 하기
            # if not context_blocks:
            #     logger.warning(f"  ⚠️ 콘텍스트 블록을 생성할 수 없습니다.")
            #     return []

            # 기존 QuestionGenerator 활용
            # TODO: context_blocks overwrite -> WHY?
            context_blocks = self.question_generator.generate_questions_for_blocks(
                blocks=context_blocks,
                num_objective=num_objective,
                num_subjective=num_subjective,
                difficulty=difficulty,
                total_test_plan=total_test_plan or {},
                document_test_plan=document_test_plan or {},
            )

            # 생성된 문제 추출 및 메타데이터 추가
            questions = []
            for block in context_blocks:
                if "questions" in block:
                    for question in block["questions"]:
                        # 문제에서 실제 사용된 키워드 추출
                        used_keywords = self._extract_used_keywords(question, keywords)

                        # 메타데이터 추가
                        question["generation_type"] = question_type
                        question["document_name"] = document_name
                        question["document_id"] = document_id
                        question["generated_at"] = datetime.now().isoformat()
                        question["source_keywords"] = used_keywords
                        questions.append(question)

            logger.info(f"  ✅ {len(questions)}개 {question_type} 문제 생성 완료")
            return questions

        except Exception as e:
            logger.error(f"  ❌ {question_type} 문제 생성 실패: {e}")
            return []

    def _convert_content_to_blocks(
        self, related_content: List[Dict], keywords: List[str]
    ) -> List[Dict]:
        """관련 콘텐츠를 블록 형태로 변환"""
        return self.vector_search_handler.convert_content_to_blocks(
            related_content, keywords
        )

    # TODO 문제에서 실제 사용된 키워드 추출 로직 점검 필요 -> [] 처리 될때 있음.
    def _extract_used_keywords(
        self, question: Dict, available_keywords: List[str]
    ) -> List[str]:
        """
        문제에서 실제 사용된 키워드만 추출

        Args:
            question: 생성된 문제 딕셔너리
            available_keywords: 사용 가능한 키워드 목록

        Returns:
            List[str]: 실제 문제에서 사용된 키워드들
        """
        used_keywords = []

        # 문제 텍스트에서 검색할 필드들
        text_fields = []

        # 문제 본문
        if question.get("question"):
            text_fields.append(question["question"])

        # 객관식 선택지
        if question.get("options"):
            text_fields.extend(question["options"])

        # 정답
        if question.get("answer"):
            text_fields.append(question["answer"])

        # 해설
        if question.get("explanation"):
            text_fields.append(question["explanation"])

        # 모든 텍스트를 하나로 합치기
        combined_text = " ".join(text_fields).lower()

        # 각 키워드가 문제 텍스트에 포함되어 있는지 확인
        for keyword in available_keywords:
            # 키워드를 소문자로 변환하여 검색 (대소문자 무시)
            if keyword.lower() in combined_text:
                used_keywords.append(keyword)
            # 키워드의 일부분이 포함된 경우도 확인 (예: "ServiceFLOW" -> "serviceflow")
            elif keyword.lower().replace(" ", "").replace("_", "").replace(
                "-", ""
            ) in combined_text.replace(" ", "").replace("_", "").replace("-", ""):
                used_keywords.append(keyword)

        return used_keywords

    def generate_questions_from_contexts(
        self,
        contexts: List[Dict[str, Any]],
        target_questions: Dict[str, int],
        document_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        배치 처리용 컨텍스트 기반 문제 생성

        Args:
            contexts: VectorDB 검색된 컨텍스트 목록
            target_questions: {"objective": 3, "subjective": 2}
            document_metadata: {
                "document_name": "doc.pdf",
                "document_id": 101,
                "keywords": ["keyword1", "keyword2"],
                "difficulty": "medium"
            }

        Returns:
            Dict: {
                "status": "success"|"failed",
                "questions": List[Dict],
                "metadata": Dict
            }
        """
        logger.info(f"🤖 배치 문제 생성 시작: {target_questions}")

        try:
            # 1. 컨텍스트를 블록 형태로 변환
            keywords = document_metadata.get("keywords", [])
            blocks = self.vector_search_handler.convert_content_to_blocks(
                contexts, keywords
            )

            if not blocks:
                return {
                    "status": "failed",
                    "error": "컨텍스트를 블록으로 변환할 수 없습니다",
                    "questions": [],
                    "metadata": {"contexts_count": len(contexts)},
                }

            # 2. 문제 생성 설정
            num_objective = target_questions.get("objective", 0)
            num_subjective = target_questions.get("subjective", 0)
            difficulty = document_metadata.get("difficulty", "NORMAL")

            # 3. 기존 QuestionGenerator 활용
            questions_blocks = self.question_generator.generate_questions_for_blocks(
                blocks=blocks,
                num_objective=num_objective,
                num_subjective=num_subjective,
                difficulty=difficulty.upper(),
            )

            # 4. 생성된 문제 추출 및 메타데이터 추가
            all_questions = []
            for block in questions_blocks:
                if "questions" in block:
                    for question in block["questions"]:
                        # 배치 처리용 메타데이터 추가
                        question["document_name"] = document_metadata.get(
                            "document_name", ""
                        )
                        question["document_id"] = document_metadata.get(
                            "document_id", 0
                        )
                        question["generated_at"] = datetime.now().isoformat()
                        question["generation_type"] = "BATCH"
                        question["source_keywords"] = self._extract_used_keywords(
                            question, keywords
                        )
                        all_questions.append(question)

            # 5. 품질 평가
            quality_score = self.calculate_question_quality(all_questions)

            # 6. 결과 반환
            result = {
                "status": "success",
                "questions": all_questions,
                "metadata": {
                    "total_questions": len(all_questions),
                    "objective_count": len(
                        [q for q in all_questions if q.get("type") == "OBJECTIVE"]
                    ),
                    "subjective_count": len(
                        [q for q in all_questions if q.get("type") == "SUBJECTIVE"]
                    ),
                    "quality_score": quality_score,
                    "contexts_used": len(contexts),
                    "keywords_used": keywords,
                    "difficulty": difficulty,
                },
            }

            logger.info(
                f"✅ 배치 문제 생성 완료: {len(all_questions)}개, 품질: {quality_score:.3f}"
            )
            return result

        except Exception as e:
            logger.error(f"❌ 배치 문제 생성 실패: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "questions": [],
                "metadata": {"contexts_count": len(contexts)},
            }

    def calculate_question_quality(self, questions: List[Dict[str, Any]]) -> float:
        """
        생성된 문제의 품질 점수 계산 (LangGraph 분기용)

        Args:
            questions: 생성된 문제 목록

        Returns:
            float: 품질 점수 (0.0-1.0)
        """
        if not questions:
            return 0.0

        total_score = 0.0
        valid_questions = 0

        for question in questions:
            question_score = 0.0

            # 1. 기본 필드 완성도 (40%)
            required_fields = ["type", "question", "answer"]
            completed_fields = sum(
                1 for field in required_fields if question.get(field)
            )
            completeness_score = completed_fields / len(required_fields)

            # 2. 타입별 추가 검증 (30%)
            type_score = 0.0
            question_type = question.get("type", "")

            if question_type == "OBJECTIVE":
                # 객관식: 선택지와 정답이 있어야 함
                options = question.get("options", [])
                answer = question.get("answer", "")
                if options and len(options) >= 2 and answer:
                    type_score = 1.0
                elif options and answer:
                    type_score = 0.7
                elif options or answer:
                    type_score = 0.3

            elif question_type == "SUBJECTIVE":
                # 주관식: 문제와 예시 답안이 있어야 함
                answer = question.get("answer", "")
                question.get("explanation", "")
                if answer and len(answer) > 10:
                    type_score = 1.0
                elif answer:
                    type_score = 0.6

            # 3. 내용 품질 (30%)
            content_score = 0.0
            question_text = question.get("question", "")

            if question_text:
                # 문제 길이 적절성
                if 10 <= len(question_text) <= 500:
                    content_score += 0.5
                elif len(question_text) > 5:
                    content_score += 0.3

                # 키워드 사용 여부
                used_keywords = question.get("source_keywords", [])
                if used_keywords:
                    content_score += 0.5
                elif question.get("keywords"):  # fallback
                    content_score += 0.3

            # 종합 점수 계산
            question_score = (
                completeness_score * 0.4 + type_score * 0.3 + content_score * 0.3
            )

            total_score += question_score
            valid_questions += 1

        # 전체 평균 점수
        average_score = total_score / valid_questions if valid_questions > 0 else 0.0
        return round(average_score, 3)
