"""
통합 PDF 파서
- Docling: 텍스트 구조화 (paragraph, section, heading)
- pdfplumber + PyMuPDF: 표 추출 (감지 + 렌더링)
- PyMuPDF: 이미지 추출 (품질 필터링)
- PyMuPDF: 차트/그래프 추출 (영역 기반)
"""

from docling.document_converter import DocumentConverter
import fitz  # PyMuPDF
import pdfplumber
import os
from typing import List, Dict, Tuple
from PIL import Image
import io
import numpy as np
from .change_name import normalize_collection_name


def parse_pdf_unified(pdf_path: str, collection_name: str = None) -> List[Dict]:
    """
    통합 PDF 파서: Docling 텍스트 구조화 + 선택적 요소 추출
    
    Args:
        pdf_path: PDF 파일 경로
        collection_name: 컬렉션명
    
    Returns:
        List[Dict]: 통합 추출된 블록들
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")
    
    if collection_name:
        normalized_name = normalize_collection_name(collection_name)
        IMAGE_SAVE_DIR = f"data/images/{normalized_name}"
    else:
        IMAGE_SAVE_DIR = "data/images/unified"
    
    os.makedirs(IMAGE_SAVE_DIR, exist_ok=True)
    
    print(f"📄 통합 파서로 PDF 처리 중: {pdf_path}")
    
    # 1. Docling으로 구조화된 텍스트 추출
    print("📝 Docling으로 텍스트 구조 추출 중...")
    text_blocks = _extract_structured_text_with_docling(pdf_path)
    
    # 2. 선택적 요소 추출 (표, 이미지, 차트)
    print("🎯 선택적 요소 추출 중...")
    visual_blocks = _extract_visual_elements(pdf_path, IMAGE_SAVE_DIR)
    
    # 3. 결합 및 정렬
    all_blocks = text_blocks + visual_blocks
    
    # 페이지별로 정렬
    all_blocks.sort(key=lambda x: x.get("metadata", {}).get("page", 0))
    
    print(f"✅ 통합 파서 완료:")
    print(f"  - 총 블록: {len(all_blocks)}개")
    print(f"  - 텍스트 블록: {len([b for b in all_blocks if b.get('type') in ['paragraph', 'section', 'heading']])}개")
    print(f"  - 표: {len([b for b in all_blocks if b.get('type') == 'table'])}개")
    print(f"  - 이미지: {len([b for b in all_blocks if b.get('type') == 'image'])}개")
    # print(f"  - 차트: {len([b for b in all_blocks if b.get('type') == 'chart'])}개")
    
    return all_blocks


def _extract_structured_text_with_docling(pdf_path: str) -> List[Dict]:
    """Docling을 사용하여 구조화된 텍스트 추출"""
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    document = result.document
    
    blocks = []
    
    try:
        # Docling의 문서 구조를 순회하여 텍스트 블록 추출
        if hasattr(document, 'texts'):
            for text_obj in document.texts:
                content = getattr(text_obj, 'text', str(text_obj)).strip()
                if content and len(content) > 10:  # 의미있는 텍스트만
                    page_no = getattr(text_obj, 'page_no', 0) + 1  # 1-indexed
                    
                    # 텍스트 타입 추론 (제목, 섹션, 일반 문단)
                    text_type = _classify_text_type(content)
                    
                    blocks.append({
                        "type": text_type,
                        "content": content,
                        "metadata": {
                            "page": page_no,
                            "extraction_method": "docling_structured",
                            "source_file": os.path.basename(pdf_path)
                        }
                    })
        
        # 섹션 제목 추가 추출 (있다면)
        if hasattr(document, 'titles'):
            for title_obj in document.titles:
                title = getattr(title_obj, 'text', str(title_obj)).strip()
                if title:
                    page_no = getattr(title_obj, 'page_no', 0) + 1
                    blocks.append({
                        "type": "section",
                        "title": title,
                        "metadata": {
                            "page": page_no,
                            "extraction_method": "docling_section",
                            "source_file": os.path.basename(pdf_path)
                        }
                    })
    
    except Exception as e:
        print(f"⚠️ Docling 구조화 추출 중 오류: {e}")
        # Fallback: 기본 텍스트 추출
        return _fallback_text_extraction(pdf_path)
    
    print(f"  📝 Docling 텍스트 블록: {len(blocks)}개")
    return blocks


def _fallback_text_extraction(pdf_path: str) -> List[Dict]:
    """Docling 실패 시 pdfplumber로 기본 텍스트 추출"""
    blocks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_no = page_num + 1
            text_content = page.extract_text()
            if text_content and text_content.strip():
                paragraphs = [p.strip() for p in text_content.split('\n\n') if p.strip() and len(p) > 20]
                for para in paragraphs:
                    blocks.append({
                        "type": "paragraph",
                        "content": para,
                        "metadata": {
                            "page": page_no,
                            "extraction_method": "pdfplumber_fallback",
                            "source_file": os.path.basename(pdf_path)
                        }
                    })
    return blocks


def _classify_text_type(content: str) -> str:
    """텍스트 내용을 기반으로 타입 분류"""
    content_lower = content.lower().strip()
    
    # 제목/헤딩 패턴
    if (len(content) < 100 and 
        (content.isupper() or 
         any(keyword in content_lower for keyword in ['챕터', 'chapter', '목차', '제', '부']) or
         content.endswith(':') or
         content.count('\n') == 0)):
        return "heading"
    
    # 섹션 패턴
    if (len(content) < 200 and 
        any(keyword in content_lower for keyword in ['그림', 'figure', '표', 'table', '부록', 'appendix'])):
        return "section"
    
    # 기본은 문단
    return "paragraph"


def _extract_visual_elements(pdf_path: str, image_save_dir: str) -> List[Dict]:
    """pdfplumber + PyMuPDF를 사용한 시각적 요소 추출"""
    blocks = []
    
    with pdfplumber.open(pdf_path) as pdf:
        pymupdf_doc = fitz.open(pdf_path)
        
        for page_num, (plumber_page, pymupdf_page) in enumerate(zip(pdf.pages, pymupdf_doc)):
            page_no = page_num + 1
            print(f"  📄 페이지 {page_no} 시각적 요소 추출 중...")
            
            # 1. 표 추출 (pdfplumber + PyMuPDF)
            table_blocks = _extract_tables(plumber_page, pymupdf_page, page_no, image_save_dir)
            blocks.extend(table_blocks)
            
            # 2. 개별 이미지 추출 (PyMuPDF + 품질 필터링)
            image_blocks = _extract_quality_images(pymupdf_page, pymupdf_doc, page_no, image_save_dir)
            blocks.extend(image_blocks)
            
            # 3. 차트 영역 추출 (주석 처리)
            # existing_bboxes = [b.get("metadata", {}).get("bbox") for b in table_blocks + image_blocks]
            # chart_blocks = _extract_chart_areas(plumber_page, pymupdf_page, page_no, image_save_dir, existing_bboxes)
            # blocks.extend(chart_blocks)
        
        pymupdf_doc.close()
    
    return blocks


def _extract_tables(plumber_page, pymupdf_page, page_no: int, image_save_dir: str) -> List[Dict]:
    """표 추출 및 렌더링"""
    blocks = []
    tables = plumber_page.extract_tables()
    
    for table_idx, table in enumerate(tables):
        if table and len(table) > 1:
            try:
                # 표 위치 추정
                table_bbox = _estimate_table_bbox(plumber_page, table)
                if table_bbox:
                    # 표 영역 이미지 추출
                    table_image = _extract_bbox_image(pymupdf_page, table_bbox, dpi=150)
                    
                    if table_image and table_image.width > 50 and table_image.height > 50:
                        table_filename = f"table_page{page_no}_{table_idx}.png"
                        table_path = os.path.join(image_save_dir, table_filename)
                        table_image.save(table_path, "PNG")
                        
                        # 표 텍스트 데이터
                        table_text = _format_table_text(table)
                        
                        blocks.append({
                            "type": "table",
                            "content": table_text,
                            "image_path": table_filename,
                            "metadata": {
                                "page": page_no,
                                "element_type": "table",
                                "element_index": table_idx,
                                "bbox": table_bbox,
                                "rows": len(table),
                                "columns": len(table[0]) if table[0] else 0,
                                "width": table_image.width,
                                "height": table_image.height,
                                "extraction_method": "pdfplumber_pymupdf_table"
                            }
                        })
                        
                        print(f"      ✅ 표 추출: {table_filename} ({len(table)}행×{len(table[0]) if table[0] else 0}열)")
            
            except Exception as e:
                print(f"      ❌ 표 추출 실패: {e}")
    
    return blocks


def _extract_quality_images(pymupdf_page, pymupdf_doc, page_no: int, image_save_dir: str) -> List[Dict]:
    """품질 필터링된 이미지 추출 (로고, 제목 등 제외)"""
    blocks = []
    image_list = pymupdf_page.get_images()
    
    # 페이지 크기 정보
    page_width = pymupdf_page.rect.width
    page_height = pymupdf_page.rect.height
    
    for img_index, img in enumerate(image_list):
        try:
            xref = img[0]
            base_image = pymupdf_doc.extract_image(xref)
            image_bytes = base_image["image"]
            
            # 기본 품질 검사
            if len(image_bytes) < 1000:
                continue
            
            pil_image = Image.open(io.BytesIO(image_bytes))
            img_width = pil_image.width
            img_height = pil_image.height
            
            # 로고/제목 필터링 조건
            if _is_logo_or_header_image(pil_image, page_width, page_height, page_no):
                print(f"      🚫 로고/헤더 이미지 제외: {img_width}×{img_height}")
                continue
            
            # 검은색 이미지 필터링
            img_array = np.array(pil_image)
            if len(img_array.shape) >= 2:
                brightness = np.mean(img_array)
                unique_colors = len(np.unique(img_array.reshape(-1) if len(img_array.shape) == 2 
                                            else img_array.reshape(-1, img_array.shape[2]), axis=0))
                
                if brightness < 10 or unique_colors < 5:
                    continue
            
            # 이미지 저장
            image_filename = f"image_page{page_no}_{img_index}.{base_image['ext']}"
            image_path = os.path.join(image_save_dir, image_filename)
            
            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)
            
            blocks.append({
                "type": "image",
                "path": image_filename,
                "metadata": {
                    "page": page_no,
                    "element_type": "standalone_image",
                    "element_index": img_index,
                    "width": img_width,
                    "height": img_height,
                    "brightness": float(brightness),
                    "unique_colors": int(unique_colors),
                    "extraction_method": "pymupdf_quality_filtered"
                }
            })
            
            print(f"      ✅ 이미지 추출: {image_filename} ({img_width}×{img_height})")
            
        except Exception as e:
            print(f"      ❌ 이미지 추출 실패: {e}")
    
    return blocks


def _is_logo_or_header_image(pil_image: Image.Image, page_width: float, page_height: float, page_no: int) -> bool:
    """로고나 헤더 이미지인지 판단"""
    img_width = pil_image.width
    img_height = pil_image.height
    aspect_ratio = img_width / img_height if img_height > 0 else 0
    
    # 1. 너무 작은 이미지 (로고 크기)
    if img_width < 200 and img_height < 200:
        return True
    
    # 2. 매우 가로로 긴 이미지 (헤더/배너)
    if aspect_ratio > 8:  # 가로:세로 비율이 8:1 이상
        return True
    
    # 3. 매우 세로로 긴 이미지 (사이드바 요소)
    if aspect_ratio < 0.2:  # 가로:세로 비율이 1:5 이하
        return True
    
    # 4. 반복되는 작은 UI 요소 (버튼, 아이콘)
    if img_width < 150 and img_height < 150:
        return True
    
    # 5. 페이지 상단/하단의 작은 요소 (헤더/푸터)
    # 이 부분은 이미지 위치 정보가 필요하므로 일단 크기만으로 판단
    if img_height < 100 and aspect_ratio > 3:  # 높이 100px 미만이면서 가로로 긴 경우
        return True
    
    # 6. 정사각형에 가까운 작은 이미지 (아이콘)
    if 0.8 <= aspect_ratio <= 1.2 and img_width < 120 and img_height < 120:
        return True
    
    return False


def _extract_chart_areas(plumber_page, pymupdf_page, page_no: int, image_save_dir: str, existing_bboxes: List) -> List[Dict]:
    """차트/그래프 영역 추출"""
    blocks = []
    chart_areas = _detect_chart_areas(plumber_page, existing_bboxes)
    
    for chart_idx, chart_bbox in enumerate(chart_areas):
        try:
            chart_image = _extract_bbox_image(pymupdf_page, chart_bbox, dpi=200)
            
            if chart_image and chart_image.width > 100 and chart_image.height > 100:
                chart_filename = f"chart_page{page_no}_{chart_idx}.png"
                chart_path = os.path.join(image_save_dir, chart_filename)
                chart_image.save(chart_path, "PNG")
                
                blocks.append({
                    "type": "chart",
                    "path": chart_filename,
                    "metadata": {
                        "page": page_no,
                        "element_type": "chart_graph",
                        "element_index": chart_idx,
                        "bbox": chart_bbox,
                        "width": chart_image.width,
                        "height": chart_image.height,
                        "extraction_method": "pymupdf_chart_render"
                    }
                })
                
                print(f"      ✅ 차트 추출: {chart_filename} ({chart_image.width}×{chart_image.height})")
                
        except Exception as e:
            print(f"      ❌ 차트 추출 실패: {e}")
    
    return blocks


# 유틸리티 함수들 (기존 selective_image_parser.py에서 가져옴)
def _estimate_table_bbox(page, table) -> Tuple[float, float, float, float]:
    """표의 대략적인 위치를 추정합니다."""
    try:
        if hasattr(page, 'find_tables'):
            tables_obj = page.find_tables()
            if tables_obj:
                return tables_obj[0].bbox
        
        # fallback: 텍스트 위치 기반 추정
        chars = page.chars
        if chars:
            page_height = page.height
            y_estimate = page_height * 0.3
            return (50, y_estimate, page.width - 50, y_estimate + 200)
        
    except Exception as e:
        print(f"표 위치 추정 실패: {e}")
    
    return None


def _extract_bbox_image(page, bbox: Tuple[float, float, float, float], dpi: int = 150) -> Image.Image:
    """지정된 영역만 이미지로 추출합니다."""
    try:
        if not bbox:
            return None
            
        x0, y0, x1, y1 = bbox
        rect = fitz.Rect(x0, y0, x1, y1)
        
        mat = fitz.Matrix(dpi/72, dpi/72)
        pix = page.get_pixmap(matrix=mat, clip=rect)
        
        img_data = pix.tobytes("png")
        pil_image = Image.open(io.BytesIO(img_data))
        
        pix = None
        return pil_image
        
    except Exception as e:
        print(f"영역 이미지 추출 실패: {e}")
        return None


def _detect_chart_areas(page, existing_bboxes: List) -> List[Tuple[float, float, float, float]]:
    """차트/그래프 영역을 휴리스틱으로 감지합니다."""
    chart_areas = []
    
    try:
        page_width = page.width
        page_height = page.height
        
        potential_areas = [
            (page_width * 0.1, page_height * 0.2, page_width * 0.9, page_height * 0.5),
            (page_width * 0.1, page_height * 0.5, page_width * 0.9, page_height * 0.8),
        ]
        
        for area in potential_areas:
            overlap = False
            for existing_bbox in existing_bboxes:
                if existing_bbox and _bbox_overlap(area, existing_bbox):
                    overlap = True
                    break
            
            if not overlap:
                chart_areas.append(area)
    
    except Exception as e:
        print(f"차트 영역 감지 실패: {e}")
    
    return chart_areas


def _bbox_overlap(bbox1: Tuple, bbox2: Tuple) -> bool:
    """두 bbox가 겹치는지 확인합니다."""
    x1_0, y1_0, x1_1, y1_1 = bbox1
    x2_0, y2_0, x2_1, y2_1 = bbox2
    
    return not (x1_1 < x2_0 or x2_1 < x1_0 or y1_1 < y2_0 or y2_1 < y1_0)


def _format_table_text(table) -> str:
    """표를 텍스트로 변환합니다."""
    table_text = ""
    for row in table:
        if row:
            row_text = " | ".join([str(cell) if cell else "" for cell in row])
            table_text += row_text + "\n"
    return table_text.strip()


# 테스트용 실행 코드
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        collection_name = sys.argv[2] if len(sys.argv) > 2 else "test_unified"
        
        if os.path.exists(pdf_path):
            blocks = parse_pdf_unified(pdf_path, collection_name)
            
            print(f"\n📊 통합 파서 결과:")
            print(f"  총 블록: {len(blocks)}개")
            print(f"  텍스트 블록: {len([b for b in blocks if b.get('type') in ['paragraph', 'section', 'heading']])}개")
            print(f"  표: {len([b for b in blocks if b.get('type') == 'table'])}개")
            print(f"  이미지: {len([b for b in blocks if b.get('type') == 'image'])}개")
            # print(f"  차트: {len([b for b in blocks if b.get('type') == 'chart'])}개")
        else:
            print(f"파일을 찾을 수 없습니다: {pdf_path}")
    else:
        print("사용법: python unified_parser.py <pdf_path> [collection_name]")