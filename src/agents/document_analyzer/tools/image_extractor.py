import io
import logging
import os
from typing import List

import fitz  # PyMuPDF
import numpy as np
from PIL import Image, ImageEnhance

logger = logging.getLogger(__name__)


def _extract_quality_images(
    pymupdf_page, pymupdf_doc, page_no: int, image_save_dir: str
) -> List[dict]:
    """하이브리드 이미지 추출: PyMuPDF + pdfplumber + 페이지 렌더링"""
    logger.info(f"  🖼️ 페이지 {page_no} 이미지 추출 시작 (하이브리드 방식)")
    blocks = []

    # 방법 1: PyMuPDF 직접 추출 (기존 방식)
    logger.debug(f"    🔍 PyMuPDF 직접 추출 방식 시작...")
    pymupdf_blocks = _extract_images_pymupdf(
        pymupdf_page, pymupdf_doc, page_no, image_save_dir
    )
    blocks.extend(pymupdf_blocks)
    logger.debug(f"    ✅ PyMuPDF 직접 추출 완료: {len(pymupdf_blocks)}개")

    # 방법 2: 페이지 렌더링 방식으로 이미지 영역 추출
    logger.debug(f"    🖼️ 페이지 렌더링 방식 시작...")
    rendered_blocks = _extract_images_rendering(pymupdf_page, page_no, image_save_dir)
    blocks.extend(rendered_blocks)
    logger.debug(f"    ✅ 페이지 렌더링 방식 완료: {len(rendered_blocks)}개")

    # 중복 제거 및 품질 기준으로 최적 선택
    logger.debug(f"    🔄 중복 제거 및 최적화 시작...")
    unique_blocks = _deduplicate_images(blocks)

    logger.info(
        f"  📊 페이지 {page_no} 이미지 추출 완료: {len(unique_blocks)}개 (총 {len(blocks)}개에서 선별)"
    )
    return unique_blocks


def _extract_images_pymupdf(
    pymupdf_page, pymupdf_doc, page_no: int, image_save_dir: str
) -> List[dict]:
    """PyMuPDF 직접 추출 방식 (기존 로직)"""
    blocks = []
    image_list = pymupdf_page.get_images()
    page_width = pymupdf_page.rect.width
    page_height = pymupdf_page.rect.height

    logger.debug(f"      🔍 PyMuPDF 직접 추출: {len(image_list)}개 이미지 감지")

    if not image_list:
        logger.debug(f"      ℹ️ 페이지 {page_no}에서 추출 가능한 이미지가 없습니다")
        return blocks

    for img_index, img in enumerate(image_list):
        try:
            xref = img[0]
            base_image = pymupdf_doc.extract_image(xref)
            image_bytes = base_image["image"]

            logger.debug(
                f"      📄 이미지 {img_index} 처리 중... (크기: {len(image_bytes)} bytes)"
            )

            if len(image_bytes) < 1000:
                logger.debug(
                    f"      🚫 이미지 {img_index} 크기 부족: {len(image_bytes)} bytes < 1000"
                )
                continue

            # 색상 공간 정보 확인
            colorspace = base_image.get("colorspace", 0)
            logger.debug(f"      🎨 색상 공간: {colorspace}")

            pil_image = Image.open(io.BytesIO(image_bytes))

            # CalGray 색상 공간(3) 특별 처리
            if colorspace == 3:  # CalGray
                pil_image = _process_calgray_image(pil_image)
                logger.debug(f"      🔧 CalGray 색상 공간 처리 적용")
            img_width = pil_image.width
            img_height = pil_image.height
            if _is_logo_or_header_image(pil_image, page_width, page_height, page_no):
                logger.debug(
                    f"      🚫 로고/헤더 이미지 제외: {img_width}×{img_height}"
                )
                continue

            # 변수 초기화
            brightness = 0
            unique_colors = 0

            img_array = np.array(pil_image)
            if len(img_array.shape) >= 2:
                brightness = np.mean(img_array)
                unique_colors = len(
                    np.unique(
                        (
                            img_array.reshape(-1)
                            if len(img_array.shape) == 2
                            else img_array.reshape(-1, img_array.shape[2])
                        ),
                        axis=0,
                    )
                )
                # 밝기 필터링 기준 조정 (10 → 80)
                if brightness < 80 or unique_colors < 5:
                    logger.debug(
                        f"      🚫 품질 필터링: 밝기={brightness:.1f}, 색상수={unique_colors}"
                    )
                    continue
            # 처리된 이미지를 저장
            image_filename = f"pymupdf_page{page_no}_{img_index}.png"
            image_path = os.path.join(image_save_dir, image_filename)
            pil_image.save(image_path, "PNG")
            blocks.append(
                {
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
                        "colorspace": colorspace,
                        "extraction_method": "pymupdf_direct",
                        "source": "pymupdf",
                    },
                }
            )
            logger.info(
                f"      ✅ PyMuPDF 추출: {image_filename} ({img_width}×{img_height})"
            )
        except Exception as e:
            logger.error(f"      ❌ 이미지 추출 실패: {e}")

    logger.debug(f"      📊 PyMuPDF 추출 결과: {len(blocks)}개 이미지 성공적으로 추출")
    return blocks


def _is_logo_or_header_image(
    pil_image: Image.Image, page_width: float, page_height: float, page_no: int
) -> bool:
    """로고나 헤더 이미지인지 판단하는 함수"""
    img_width = pil_image.width
    img_height = pil_image.height
    aspect_ratio = img_width / img_height if img_height > 0 else 0

    # 각 조건별로 상세 로깅
    if img_width < 200 and img_height < 200:
        logger.debug(f"      🔍 로고/헤더 판단: 작은 크기 ({img_width}×{img_height})")
        return True
    if aspect_ratio > 8:
        logger.debug(
            f"      🔍 로고/헤더 판단: 가로 비율 과도 (비율: {aspect_ratio:.2f})"
        )
        return True
    if aspect_ratio < 0.2:
        logger.debug(
            f"      🔍 로고/헤더 판단: 세로 비율 과도 (비율: {aspect_ratio:.2f})"
        )
        return True
    if img_width < 150 and img_height < 150:
        logger.debug(
            f"      🔍 로고/헤더 판단: 매우 작은 크기 ({img_width}×{img_height})"
        )
        return True
    if img_height < 100 and aspect_ratio > 3:
        logger.debug(
            f"      🔍 로고/헤더 판단: 얇은 배너형 (높이: {img_height}, 비율: {aspect_ratio:.2f})"
        )
        return True
    if 0.8 <= aspect_ratio <= 1.2 and img_width < 120 and img_height < 120:
        logger.debug(
            f"      🔍 로고/헤더 판단: 작은 정사각형 ({img_width}×{img_height})"
        )
        return True

    return False


def _process_calgray_image(pil_image: Image.Image) -> Image.Image:
    """CalGray 색상 공간 이미지 후처리"""
    logger.debug(f"      🎨 CalGray 이미지 후처리 시작...")

    try:
        # RGB 모드로 변환 (이미 RGB일 수도 있음)
        if pil_image.mode != "RGB":
            logger.debug(f"      🔄 색상 모드 변환: {pil_image.mode} → RGB")
            pil_image = pil_image.convert("RGB")
        else:
            logger.debug(f"      ℹ️ 이미 RGB 모드입니다")

        # 이미지 통계 확인
        img_array = np.array(pil_image)
        original_brightness = np.mean(img_array)

        # 매우 어두운 이미지인 경우에만 처리
        if original_brightness < 120:
            logger.debug(
                f"      🔧 어두운 이미지 감지 (밝기: {original_brightness:.1f}), 후처리 적용"
            )

            # 명도 조정
            enhancer = ImageEnhance.Brightness(pil_image)
            pil_image = enhancer.enhance(1.5)  # 밝기 50% 증가

            # 대비 조정
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(1.3)  # 대비 30% 증가

            # 처리 후 밝기 확인
            processed_array = np.array(pil_image)
            processed_brightness = np.mean(processed_array)
            logger.debug(
                f"      ✨ 후처리 완료: {original_brightness:.1f} → {processed_brightness:.1f}"
            )
        else:
            logger.debug(
                f"      ✅ 이미지가 충분히 밝음 (밝기: {original_brightness:.1f}), 후처리 생략"
            )

        return pil_image

    except Exception as e:
        logger.warning(f"      ⚠️ CalGray 이미지 처리 실패: {e}")
        return pil_image


def _extract_images_rendering(
    pymupdf_page, page_no: int, image_save_dir: str
) -> List[dict]:
    """페이지 렌더링 방식으로 이미지 영역 추출"""
    blocks = []

    logger.debug(f"      🖼️ 페이지 렌더링 방식으로 이미지 영역 추출 중...")

    try:
        # 고해상도로 페이지 렌더링
        logger.debug(f"      📸 페이지를 2배 해상도로 렌더링 중...")
        mat = fitz.Matrix(2.0, 2.0)  # 2배 확대
        pix = pymupdf_page.get_pixmap(matrix=mat)
        img_data = pix.pil_tobytes(format="PNG")
        page_image = Image.open(io.BytesIO(img_data))
        logger.debug(
            f"      ✅ 페이지 렌더링 완료: {page_image.width}×{page_image.height}"
        )

        # 이미지 리스트에서 위치 정보 가져오기
        image_list = pymupdf_page.get_images()
        logger.debug(f"      📋 렌더링에서 처리할 이미지 수: {len(image_list)}개")

        if not image_list:
            logger.debug(f"      ℹ️ 렌더링 방식으로 처리할 이미지가 없습니다")
            return blocks

        for img_index, img in enumerate(image_list):
            try:
                # 이미지 위치 정보 가져오기
                xref = img[0]
                img_rects = [r for r in pymupdf_page.get_image_rects(xref)]

                logger.debug(
                    f"      📍 이미지 {img_index}: {len(img_rects)}개 위치 발견"
                )

                if not img_rects:
                    logger.debug(f"      ⚠️ 이미지 {img_index}: 위치 정보 없음")
                    continue

                for rect_index, rect in enumerate(img_rects):
                    logger.debug(
                        f"      🔲 이미지 {img_index}-{rect_index} 영역 추출 중: ({rect.x0:.1f}, {rect.y0:.1f}, {rect.x1:.1f}, {rect.y1:.1f})"
                    )

                    # 좌표를 렌더링 스케일에 맞게 조정
                    x0 = int(rect.x0 * 2)
                    y0 = int(rect.y0 * 2)
                    x1 = int(rect.x1 * 2)
                    y1 = int(rect.y1 * 2)

                    # 영역 추출
                    if x1 > x0 and y1 > y0:
                        cropped_image = page_image.crop((x0, y0, x1, y1))
                        logger.debug(
                            f"      ✂️ 영역 추출 완료: {cropped_image.width}×{cropped_image.height}"
                        )

                        # 크기 확인
                        if cropped_image.width < 50 or cropped_image.height < 50:
                            logger.debug(
                                f"      🚫 크기 부족: {cropped_image.width}×{cropped_image.height} < 50×50"
                            )
                            continue

                        # 로고/헤더 필터링
                        if _is_logo_or_header_image(
                            cropped_image,
                            pymupdf_page.rect.width,
                            pymupdf_page.rect.height,
                            page_no,
                        ):
                            logger.debug(
                                f"      🚫 로고/헤더 이미지 제외: {cropped_image.width}×{cropped_image.height}"
                            )
                            continue

                        # 품질 분석
                        img_array = np.array(cropped_image)
                        if len(img_array.shape) >= 2:
                            brightness = np.mean(img_array)
                            unique_colors = len(
                                np.unique(
                                    (
                                        img_array.reshape(-1)
                                        if len(img_array.shape) == 2
                                        else img_array.reshape(-1, img_array.shape[2])
                                    ),
                                    axis=0,
                                )
                            )

                            # 품질 필터링 (렌더링 방식은 더 관대한 기준 적용)
                            if brightness < 50 or unique_colors < 3:
                                logger.debug(
                                    f"      🚫 렌더링 품질 필터링: 밝기={brightness:.1f}, 색상수={unique_colors}"
                                )
                                continue

                            # 이미지 저장
                            image_filename = (
                                f"rendered_page{page_no}_{img_index}_{rect_index}.png"
                            )
                            image_path = os.path.join(image_save_dir, image_filename)
                            cropped_image.save(image_path, "PNG")

                            blocks.append(
                                {
                                    "type": "image",
                                    "path": image_filename,
                                    "metadata": {
                                        "page": page_no,
                                        "element_type": "rendered_image",
                                        "element_index": f"{img_index}_{rect_index}",
                                        "width": cropped_image.width,
                                        "height": cropped_image.height,
                                        "brightness": float(brightness),
                                        "unique_colors": int(unique_colors),
                                        "extraction_method": "page_rendering",
                                        "source": "rendering",
                                        "rect": [
                                            x0 / 2,
                                            y0 / 2,
                                            x1 / 2,
                                            y1 / 2,
                                        ],  # 원본 좌표
                                    },
                                }
                            )

                            logger.debug(
                                f"      ✅ 렌더링 추출: {image_filename} ({cropped_image.width}×{cropped_image.height})"
                            )
                    else:
                        logger.debug(
                            f"      🚫 유효하지 않은 좌표: ({x0}, {y0}, {x1}, {y1})"
                        )

            except Exception as e:
                logger.warning(f"      ⚠️ 렌더링 추출 실패 (이미지 {img_index}): {e}")
                continue

    except Exception as e:
        logger.error(f"      ❌ 페이지 렌더링 실패: {e}")

    logger.debug(f"      📊 렌더링 방식으로 {len(blocks)}개 이미지 추출")
    return blocks


def _deduplicate_images(blocks: List[dict]) -> List[dict]:
    """중복 이미지 제거 및 최적 선택"""
    if not blocks:
        logger.debug(f"      ℹ️ 중복 제거할 이미지가 없습니다")
        return []

    logger.debug(f"      🔄 중복 제거 전: {len(blocks)}개 이미지")

    # 페이지별로 그룹화
    page_groups = {}
    for block in blocks:
        page = block.get("metadata", {}).get("page", 0)
        if page not in page_groups:
            page_groups[page] = []
        page_groups[page].append(block)

    logger.debug(f"      📊 페이지별 그룹화: {len(page_groups)}개 페이지")

    unique_blocks = []

    for page, page_blocks in page_groups.items():
        # 각 페이지에서 중복 제거
        pymupdf_blocks = [
            b for b in page_blocks if b.get("metadata", {}).get("source") == "pymupdf"
        ]
        rendered_blocks = [
            b for b in page_blocks if b.get("metadata", {}).get("source") == "rendering"
        ]

        logger.debug(
            f"      📄 페이지 {page}: PyMuPDF {len(pymupdf_blocks)}개, 렌더링 {len(rendered_blocks)}개"
        )

        # 렌더링 방식 우선 선택 (더 나은 색상 처리)
        if rendered_blocks:
            selected_rendered = 0
            # 렌더링 블록 중 가장 품질 좋은 것들 선택
            for block in rendered_blocks:
                brightness = block.get("metadata", {}).get("brightness", 0)
                if brightness > 100:  # 충분히 밝은 이미지만
                    unique_blocks.append(block)
                    selected_rendered += 1
            logger.debug(
                f"      ✨ 페이지 {page}: 렌더링 방식에서 {selected_rendered}개 선택 (밝기 > 100)"
            )

        # 렌더링에서 얻지 못한 이미지는 PyMuPDF에서 보완
        if not rendered_blocks and pymupdf_blocks:
            selected_pymupdf = 0
            for block in pymupdf_blocks:
                brightness = block.get("metadata", {}).get("brightness", 0)
                if brightness > 80:  # PyMuPDF는 더 엄격한 기준
                    unique_blocks.append(block)
                    selected_pymupdf += 1
            logger.debug(
                f"      ✨ 페이지 {page}: PyMuPDF 방식에서 {selected_pymupdf}개 선택 (밝기 > 80)"
            )

    logger.debug(f"      ✨ 중복 제거 후: {len(unique_blocks)}개 이미지")
    return unique_blocks
