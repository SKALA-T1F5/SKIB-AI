import logging
import os
from typing import List

logger = logging.getLogger(__name__)


def _extract_tables(
    plumber_page, pymupdf_page, page_no: int, image_save_dir: str
) -> List[dict]:
    """
    테이블 추출 (중복 제거 개선 버전)

    Args:
        plumber_page: pdfplumber 페이지 객체
        pymupdf_page: PyMuPDF 페이지 객체
        page_no: 페이지 번호
        image_save_dir: 이미지 저장 디렉토리

    Returns:
        List[dict]: 중복이 제거된 테이블 블록 리스트
    """
    from .extract_utils import (
        _estimate_table_bbox,
        _extract_bbox_image,
        _remove_duplicate_tables,
    )

    blocks = []
    tables = plumber_page.extract_tables()

    logger.info(f"      📊 {len(tables)}개 테이블 감지됨")

    for table_idx, table in enumerate(tables):
        if table and len(table) > 1:
            try:
                # 개선된 bbox 추정 (테이블 인덱스 전달)
                table_bbox = _estimate_table_bbox(plumber_page, table, table_idx)
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

                        # 메타데이터에 bbox 정보 추가 (중복 제거용)
                        blocks.append(
                            {
                                "type": "table",
                                "content": table_text,
                                "path": table_filename,
                                "metadata": {
                                    "page": page_no,
                                    "element_type": "table",
                                    "element_index": table_idx,
                                    "bbox": table_bbox,  # 중복 제거를 위한 bbox 정보
                                    "rows": len(table),
                                    "columns": len(table[0]) if table[0] else 0,
                                    "width": table_image.width,
                                    "height": table_image.height,
                                    "extraction_method": "pdfplumber_pymupdf_table",
                                },
                            }
                        )
                        logger.info(
                            f"      ✅ 표 추출: {table_filename} ({len(table)}행×{len(table[0]) if table[0] else 0}열)"
                        )
                else:
                    logger.warning(f"      ⚠️ 테이블 {table_idx} bbox 추정 실패")
            except Exception as e:
                logger.error(f"      ❌ 표 추출 실패 (테이블 {table_idx}): {e}")

    # 중복 제거 적용
    if len(blocks) > 1:
        logger.debug(f"      🔄 중복 테이블 검사 중... ({len(blocks)}개)")
        unique_blocks = _remove_duplicate_tables(blocks, overlap_threshold=0.7)
        removed_count = len(blocks) - len(unique_blocks)
        logger.debug(f"      ✅ 중복 검사 완료: {len(unique_blocks)}개 유지")

        if removed_count > 0:
            logger.info(f"      ✨ 중복 테이블 {removed_count}개 제거됨")

        return unique_blocks

    return blocks


def _format_table_text(table) -> str:
    table_text = ""
    for row in table:
        if row:
            row_text = " | ".join([str(cell) if cell else "" for cell in row])
            table_text += row_text + "\n"
    return table_text.strip()
