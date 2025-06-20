# """
# Question Generation Pipeline

# 이 모듈은 PDF 문서에서 자동으로 문제를 생성하는 파이프라인을 제공합니다.

# 주요 기능:
# - PDF 파싱 및 블록 분해
# - GPT-4o Vision을 사용한 자동 문제 생성
# - 메타데이터 및 결과 저장

# 사용법:
#     from src.pipelines.question_generation import run_question_generation_pipeline

#     results = run_question_generation_pipeline(
#         pdf_path="data/raw_docs/sample.pdf",
#         num_objective=5,
#         num_subjective=3
#     )
# """

# from .run_pipeline import run_pipeline, run_question_generation_pipeline

# __all__ = ["run_question_generation_pipeline", "run_pipeline"]
