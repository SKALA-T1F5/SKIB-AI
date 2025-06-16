from typing import List, Tuple
from .extract_utils import _extract_bbox_image

def _extract_chart_areas(plumber_page, pymupdf_page, page_no: int, image_save_dir: str, existing_bboxes: List) -> List[dict]:
    chart_areas = _detect_chart_areas(plumber_page, existing_bboxes)
    blocks = []
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

def _detect_chart_areas(page, existing_bboxes: List) -> List[Tuple[float, float, float, float]]:
    chart_areas = []
    try:
        page_width = page.width
        page_height = page.height
        potential_areas = [
            (page_width * 0.1, page_height * 0.2, page_width * 0.9, page_height * 0.5),
            (page_width * 0.1, page_height * 0.5, page_width * 0.9, page_height * 0.8),
        ]
        from .extract_utils import _bbox_overlap
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
