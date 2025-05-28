# 코드 설명 : PDF 파일을 열고 각 페이지의 텍스트를 추출하여 간단한 문단 단위(paragraph) 블록 리스트로 변환
# 이후 표, 리스트, 이미지 블록을 포함하고 싶다면 get_text("dict"), get_text("blocks"), page.get_images() 등을 사용하는 방식으로 확장 가능.

import fitz  # PyMuPDF(PDF 파일을 열고 텍스트, 이미지 등을 추출)


def parse_pdf_to_docling_blocks(pdf_path: str) -> list:
    """
    PDF 파일을 열어 간단한 paragraph 블록 리스트로 변환.
    실제 Docling 모델 대체 전 임시 구현.
    """
    doc = fitz.open(pdf_path)  # PDF 문서 열기
    blocks = []
    for i, page in enumerate(doc):
        text = page.get_text().strip()  # 페이지에서 전체 텍스트 추출 후 앞뒤 공백 제거
        if text:
            paragraphs = text.split("\n")  # 줄바꿈 단위로 문단 나누기
            for p in paragraphs:
                clean = p.strip()  # 각 문단의 앞뒤 공백 제거
                if clean:
                    blocks.append({"type": "paragraph", "content": clean})
    return blocks
