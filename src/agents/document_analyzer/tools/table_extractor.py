import os
from typing import List


def _extract_tables(
    plumber_page, pymupdf_page, page_no: int, image_save_dir: str
) -> List[dict]:
    from .extract_utils import _estimate_table_bbox, _extract_bbox_image

    blocks = []
    tables = plumber_page.extract_tables()
    for table_idx, table in enumerate(tables):
        if table and len(table) > 1:
            try:
                table_bbox = _estimate_table_bbox(plumber_page, table)
                if table_bbox:
                    table_image = _extract_bbox_image(pymupdf_page, table_bbox, dpi=150)
                    if (
                        table_image
                        and table_image.width > 50
                        and table_image.height > 50
                    ):
                        table_filename = f"table_page{page_no}_{table_idx}.png"
                        table_path = os.path.join(image_save_dir, table_filename)
                        table_image.save(table_path, "PNG")
                        table_text = _format_table_text(table)
                        blocks.append(
                            {
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
                                    "extraction_method": "pdfplumber_pymupdf_table",
                                },
                            }
                        )
                        print(
                            f"      ✅ 표 추출: {table_filename} ({len(table)}행×{len(table[0]) if table[0] else 0}열)"
                        )
            except Exception as e:
                print(f"      ❌ 표 추출 실패: {e}")
    return blocks


def _format_table_text(table) -> str:
    table_text = ""
    for row in table:
        if row:
            row_text = " | ".join([str(cell) if cell else "" for cell in row])
            table_text += row_text + "\n"
    return table_text.strip()
