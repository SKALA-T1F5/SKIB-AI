import io
from typing import Tuple, List, Dict

import fitz
from PIL import Image


def _estimate_table_bbox(page, table, table_index: int = 0) -> Tuple[float, float, float, float]:
    """
    테이블의 bbox 추정 (개선된 버전)
    
    Args:
        page: pdfplumber 페이지 객체
        table: 테이블 데이터
        table_index: 테이블 인덱스 (여러 테이블 구분용)
    
    Returns:
        Tuple: (x0, y0, x1, y1) bbox 좌표
    """
    try:
        # pdfplumber의 find_tables를 사용하여 정확한 bbox 추출
        if hasattr(page, "find_tables"):
            tables_obj = page.find_tables()
            if tables_obj and len(tables_obj) > table_index:
                # 해당 인덱스의 테이블 bbox 반환
                return tables_obj[table_index].bbox
        
        # 폴백: 테이블 데이터를 기반으로 더 정교한 추정
        if table and len(table) > 0:
            chars = page.chars
            if chars:
                # 테이블의 첫 번째 행에서 실제 텍스트 위치 찾기
                first_row = table[0] if table[0] else []
                if first_row and any(cell and str(cell).strip() for cell in first_row):
                    # 첫 번째 비어있지 않은 셀의 텍스트로 위치 추정
                    first_cell_text = next((str(cell).strip() for cell in first_row if cell and str(cell).strip()), None)
                    
                    if first_cell_text:
                        # 해당 텍스트가 포함된 문자들의 위치 찾기
                        matching_chars = [c for c in chars if first_cell_text[:10] in (c.get('text', '') or '')]
                        if matching_chars:
                            min_x = min(c['x0'] for c in matching_chars)
                            min_y = min(c['y0'] for c in matching_chars)
                            max_x = max(c['x1'] for c in matching_chars)
                            
                            # 테이블 크기 추정 (행 수 기반)
                            estimated_height = len(table) * 20  # 행당 대략 20pt
                            estimated_width = max(300, max_x - min_x + 100)  # 최소 300pt
                            
                            return (
                                max(min_x - 20, 0),  # 여백 추가
                                max(min_y - 10, 0),
                                min(min_x + estimated_width, page.width),
                                min(min_y + estimated_height, page.height)
                            )
        
        # 최종 폴백: 테이블 인덱스를 고려한 추정 위치
        page_height = page.height
        page_width = page.width
        
        # 테이블 인덱스에 따라 Y 위치 조정
        y_offset = table_index * 150  # 테이블간 간격
        y_estimate = page_height * 0.2 + y_offset  # 페이지 상단 20% + 오프셋
        
        # 페이지 범위를 벗어나지 않도록 조정
        if y_estimate + 200 > page_height:
            y_estimate = max(page_height * 0.1, page_height - 250)
        
        return (
            50,  # 좌측 여백
            y_estimate,
            page_width - 50,  # 우측 여백
            min(y_estimate + 200, page_height)  # 테이블 높이
        )
    
    except Exception as e:
        print(f"표 위치 추정 실패 (테이블 {table_index}): {e}")
    
    return None


def _extract_bbox_image(
    page, bbox: Tuple[float, float, float, float], dpi: int = 150
) -> Image.Image:
    try:
        if not bbox:
            return None
        x0, y0, x1, y1 = bbox
        rect = fitz.Rect(x0, y0, x1, y1)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat, clip=rect)
        img_data = pix.tobytes("png")
        pil_image = Image.open(io.BytesIO(img_data))
        pix = None
        return pil_image
    except Exception as e:
        print(f"영역 이미지 추출 실패: {e}")
        return None


def _bbox_overlap(bbox1: Tuple, bbox2: Tuple) -> bool:
    x1_0, y1_0, x1_1, y1_1 = bbox1
    x2_0, y2_0, x2_1, y2_1 = bbox2
    return not (x1_1 < x2_0 or x2_1 < x1_0 or y1_1 < y2_0 or y2_1 < y1_0)


def _calculate_overlap_ratio(bbox1: Tuple[float, float, float, float], bbox2: Tuple[float, float, float, float]) -> float:
    """
    두 bbox 간의 겹침 비율 계산
    
    Args:
        bbox1: 첫 번째 bbox (x0, y0, x1, y1)
        bbox2: 두 번째 bbox (x0, y0, x1, y1)
    
    Returns:
        float: 겹침 비율 (0.0 ~ 1.0)
    """
    try:
        x1_0, y1_0, x1_1, y1_1 = bbox1
        x2_0, y2_0, x2_1, y2_1 = bbox2
        
        # 교집합 계산
        intersect_x0 = max(x1_0, x2_0)
        intersect_y0 = max(y1_0, y2_0)
        intersect_x1 = min(x1_1, x2_1)
        intersect_y1 = min(y1_1, y2_1)
        
        # 교집합이 없는 경우
        if intersect_x1 <= intersect_x0 or intersect_y1 <= intersect_y0:
            return 0.0
        
        # 교집합 넓이
        intersect_area = (intersect_x1 - intersect_x0) * (intersect_y1 - intersect_y0)
        
        # 각 bbox의 넓이
        area1 = (x1_1 - x1_0) * (y1_1 - y1_0)
        area2 = (x2_1 - x2_0) * (y2_1 - y2_0)
        
        # 합집합 넓이
        union_area = area1 + area2 - intersect_area
        
        # IoU (Intersection over Union) 계산
        return intersect_area / union_area if union_area > 0 else 0.0
        
    except Exception as e:
        print(f"겹침 비율 계산 실패: {e}")
        return 0.0


def _remove_duplicate_tables(table_blocks: List[Dict], overlap_threshold: float = 0.8) -> List[Dict]:
    """
    중복 테이블 제거
    
    Args:
        table_blocks: 테이블 블록 리스트
        overlap_threshold: 중복 판정 임계값 (0.0 ~ 1.0)
    
    Returns:
        List[Dict]: 중복이 제거된 테이블 블록 리스트
    """
    if not table_blocks:
        return []
    
    unique_blocks = []
    
    for block in table_blocks:
        is_duplicate = False
        current_bbox = block.get("metadata", {}).get("bbox")
        
        if not current_bbox:
            unique_blocks.append(block)
            continue
        
        for i, existing_block in enumerate(unique_blocks):
            existing_bbox = existing_block.get("metadata", {}).get("bbox")
            
            if not existing_bbox:
                continue
            
            # 겹침 비율 계산
            overlap_ratio = _calculate_overlap_ratio(current_bbox, existing_bbox)
            
            if overlap_ratio > overlap_threshold:
                is_duplicate = True
                
                # 더 나은 테이블 선택 기준
                current_rows = block.get("metadata", {}).get("rows", 0)
                current_cols = block.get("metadata", {}).get("columns", 0)
                current_area = (current_bbox[2] - current_bbox[0]) * (current_bbox[3] - current_bbox[1])
                
                existing_rows = existing_block.get("metadata", {}).get("rows", 0)
                existing_cols = existing_block.get("metadata", {}).get("columns", 0)
                existing_area = (existing_bbox[2] - existing_bbox[0]) * (existing_bbox[3] - existing_bbox[1])
                
                # 더 많은 행/열을 가지거나 더 큰 면적을 가진 테이블을 우선 선택
                current_score = current_rows * current_cols + current_area * 0.01
                existing_score = existing_rows * existing_cols + existing_area * 0.01
                
                if current_score > existing_score:
                    # 현재 테이블이 더 좋으면 기존 테이블 교체
                    unique_blocks[i] = block
                    print(f"      🔄 더 나은 테이블로 교체: {current_rows}행×{current_cols}열 (기존: {existing_rows}행×{existing_cols}열)")
                else:
                    print(f"      🚫 중복 테이블 스킵: {current_rows}행×{current_cols}열")
                
                break
        
        if not is_duplicate:
            unique_blocks.append(block)
    
    return unique_blocks
