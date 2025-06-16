from typing import Tuple, List
import fitz
from PIL import Image
import io

def _estimate_table_bbox(page, table) -> Tuple[float, float, float, float]:
    try:
        if hasattr(page, 'find_tables'):
            tables_obj = page.find_tables()
            if tables_obj:
                return tables_obj[0].bbox
        chars = page.chars
        if chars:
            page_height = page.height
            y_estimate = page_height * 0.3
            return (50, y_estimate, page.width - 50, y_estimate + 200)
    except Exception as e:
        print(f"표 위치 추정 실패: {e}")
    return None

def _extract_bbox_image(page, bbox: Tuple[float, float, float, float], dpi: int = 150) -> Image.Image:
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

def _bbox_overlap(bbox1: Tuple, bbox2: Tuple) -> bool:
    x1_0, y1_0, x1_1, y1_1 = bbox1
    x2_0, y2_0, x2_1, y2_1 = bbox2
    return not (x1_1 < x2_0 or x2_1 < x1_0 or y1_1 < y2_0 or y2_1 < y1_0)
