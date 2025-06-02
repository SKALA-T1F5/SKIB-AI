"""
Docling을 사용하여 PDF 문서를 파싱하고 paragraph, image, section 중심의 구조화된 블록으로 변환합니다.
Table, List 블록은 토큰 사용량 최적화를 위해 현재 단계에서는 건너뜁니다.
"""

from docling.document_converter import DocumentConverter
import os
from typing import List, Dict

IMAGE_SAVE_DIR = "data/images" # 이미지 저장 디렉토리

def parse_pdf_to_docling_blocks(pdf_path: str) -> List[Dict]:
    """
    PDF 파일을 Docling을 사용하여 paragraph, image, section 블록으로 변환합니다.
    Table 및 List 블록은 건너뜁니다.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)

    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    document = result.document
    
    blocks = []
    image_counter = 0 # 저장되는 이미지 파일명 중복 방지

    # Docling의 블록 구조는 복잡할 수 있으므로, 주요 요소들을 순회하며 필요한 블록 유형을 구성합니다.
    # Docling은 페이지별 명시적 반복보다는 전체 문서 구조를 기반으로 요소를 제공하는 경우가 많습니다.
    # 따라서, 각 요소에서 페이지 번호(page_no)를 추출하는 것이 중요합니다.

    # 1. 텍스트 블록 (Paragraphs) 및 잠재적 섹션 타이틀
    # Docling의 'texts'는 일반 텍스트 덩어리일 수 있고, 'titles' 또는 'headings' 같은 속성으로 섹션 제목을 얻을 수 있습니다.
    # 여기서는 DocumentConverter가 생성하는 'texts' 객체와 'titles' (가정)을 활용합니다.
    # 실제 Docling API에 따라 'document.headings' 또는 다른 속성을 확인해야 할 수 있습니다.

    if hasattr(document, 'titles'): # 섹션 제목이 'titles' 속성에 있다고 가정
        for title_obj in document.titles:
            page_no = getattr(title_obj, 'page_no', 0) + 1 # 1-indexed
            blocks.append({
                "type": "section",
                "title": getattr(title_obj, 'text', str(title_obj)),
                "metadata": {"page": page_no}
            })

    if hasattr(document, 'texts'):
        for text_obj in document.texts:
            # 이미 title로 처리된 내용과 중복되지 않도록 하는 로직이 필요할 수 있으나, 여기서는 단순화.
            page_no = getattr(text_obj, 'page_no', 0) + 1 # 1-indexed
            content = getattr(text_obj, 'text', str(text_obj)).strip()
            if content: # 내용이 있는 경우에만 추가
                blocks.append({
                    "type": "paragraph",
                    "content": content,
                    "metadata": {"page": page_no}
                })

    # 2. 이미지 블록
    if hasattr(document, 'pictures'):
        for pic_obj in document.pictures:
            if hasattr(pic_obj, 'image') and pic_obj.image:
                page_no = getattr(pic_obj, 'page_no', 0) + 1 # 1-indexed
                
                # 이미지 저장 (Pillow Image 객체라고 가정)
                try:
                    # Docling에서 이미지 ID나 원래 파일명을 얻을 수 있다면 사용하는 것이 좋음
                    # 여기서는 단순 카운터 기반으로 파일명 생성
                    image_filename = f"docling_page{page_no}_img{image_counter}.png" # 확장자는 .png로 가정
                    if hasattr(pic_obj.image, 'format') and pic_obj.image.format:
                        image_ext = pic_obj.image.format.lower()
                        if image_ext not in ['jpeg', 'png', 'gif', 'bmp']: # 일반적인 확장자 아니면 png로
                             image_ext = 'png'
                        image_filename = f"docling_page{page_no}_img{image_counter}.{image_ext}"
                    
                    image_save_path = os.path.join(IMAGE_SAVE_DIR, image_filename)
                    pic_obj.image.save(image_save_path)
                    
                    blocks.append({
                        "type": "image",
                        "path": image_filename, # preprocess_docling.py에서 IMAGE_SAVE_DIR와 조합될 상대 경로
                        "metadata": {"page": page_no}
                    })
                    image_counter += 1
                except Exception as e:
                    print(f"Docling 이미지 저장/처리 실패 (페이지 {page_no}): {e}")

    # 3. Table 및 List 블록은 건너뛰기 (토큰 최적화)
    if hasattr(document, 'tables'):
        print(f"Skipping {len(document.tables)} table blocks for token optimization.")
    
    if hasattr(document, 'lists') or hasattr(document, 'groups'): # 'groups'가 리스트로 사용될 수 있음
        num_lists = 0
        if hasattr(document, 'lists'):
            num_lists += len(document.lists)
        if hasattr(document, 'groups'): # groups가 실제 list와 유사한 구조인지 확인 필요
             num_lists += len(document.groups) # 단순 합산, 실제로는 구분 필요
        if num_lists > 0:
            print(f"Skipping {num_lists} list/group blocks for token optimization.")
            
    # Docling은 블록 순서를 문서 순서대로 제공할 것으로 기대하지만,
    # 필요하다면 페이지 번호와 블록 내 위치(bbox 등)를 기준으로 정렬할 수 있습니다.
    # 여기서는 Docling의 순서를 따릅니다.
    # 페이지 번호 기준으로 한 번 정렬해주는 것이 좋을 수 있습니다.
    try:
        blocks.sort(key=lambda b: b.get('metadata', {}).get('page', 0))
    except Exception as e:
        print(f"블록 정렬 중 오류 발생: {e}. 페이지 순서가 정확하지 않을 수 있습니다.")


    print(f"Total blocks extracted by Docling (paragraph, image, section only): {len(blocks)}")
    if not blocks:
        print("Warning: No blocks were extracted by Docling or all were skipped.")
        if hasattr(document, 'num_pages'):
             print(f"Number of pages in PDF by Docling: {document.num_pages}")

    return blocks

# 사용 예시 (테스트용)
if __name__ == '__main__':
    # 테스트할 PDF 파일 경로를 지정하세요.
    # 예: test_pdf_path = "path/to/your/test.pdf"
    # 이 스크립트와 같은 디렉토리에 example.pdf가 있다고 가정합니다.
    
    # Docling은 실제 PDF 파일이 필요합니다. fitz로 임시 PDF 만드는 것은 Docling 테스트에 부적합.
    # 실제 PDF 파일 경로를 여기에 입력하세요.
    test_pdf_file = "example.pdf" # << 실제 테스트 시 유효한 PDF 파일명으로 변경하세요!
                                  # 예를 들어, 이전 단계에서 생성된 example.pdf (fitz 기반)는
                                  # Docling으로 테스트하기에 부적절할 수 있습니다.
                                  # Docling이 잘 처리할 수 있는 실제 PDF로 테스트해야 합니다.

    if os.path.exists(test_pdf_file) and test_pdf_file.endswith(".pdf"):
        print(f"Testing with PDF: {test_pdf_file} using Docling")
        try:
            extracted_blocks = parse_pdf_to_docling_blocks(test_pdf_file)
            for i, block in enumerate(extracted_blocks):
                page_info = block.get('metadata', {}).get('page', 'N/A')
                print(f"Block {i}: Type={block.get('type')}, Page={page_info}")
                if block.get('type') == 'paragraph':
                    print(f"  Content: {block.get('content', '')[:50]}...")
                elif block.get('type') == 'section':
                    print(f"  Title: {block.get('title', '')[:50]}...")
                elif block.get('type') == 'image':
                    print(f"  Path: {block.get('path')}")
            
            # 테스트 후 생성된 이미지 디렉토리/파일 정리 (선택적)
            # import shutil
            # if os.path.exists(IMAGE_SAVE_DIR) and len(os.listdir(IMAGE_SAVE_DIR)) > 0 :
            #     # shutil.rmtree(IMAGE_SAVE_DIR) # 주의: 디렉토리 전체 삭제
            #     # print(f"Cleaned up directory: {IMAGE_SAVE_DIR}")
            #     pass
        except FileNotFoundError as e:
            print(e)
        except ImportError:
            print("Docling 라이브러리가 설치되지 않았을 수 있습니다. pip install docling")
        except Exception as e:
            print(f"An error occurred during Docling test: {e}")
    else:
        print(f"Test PDF file not found or not a PDF: {test_pdf_file}. Please provide a valid PDF path for Docling testing.")
