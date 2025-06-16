from typing import List
import os
from PIL import Image
import io
import numpy as np

def _extract_quality_images(pymupdf_page, pymupdf_doc, page_no: int, image_save_dir: str) -> List[dict]:
    blocks = []
    image_list = pymupdf_page.get_images()
    page_width = pymupdf_page.rect.width
    page_height = pymupdf_page.rect.height
    for img_index, img in enumerate(image_list):
        try:
            xref = img[0]
            base_image = pymupdf_doc.extract_image(xref)
            image_bytes = base_image["image"]
            if len(image_bytes) < 1000:
                continue
            pil_image = Image.open(io.BytesIO(image_bytes))
            img_width = pil_image.width
            img_height = pil_image.height
            if _is_logo_or_header_image(pil_image, page_width, page_height, page_no):
                print(f"      🚫 로고/헤더 이미지 제외: {img_width}×{img_height}")
                continue
            img_array = np.array(pil_image)
            if len(img_array.shape) >= 2:
                brightness = np.mean(img_array)
                unique_colors = len(np.unique(img_array.reshape(-1) if len(img_array.shape) == 2 
                                            else img_array.reshape(-1, img_array.shape[2]), axis=0))
                if brightness < 10 or unique_colors < 5:
                    continue
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
    img_width = pil_image.width
    img_height = pil_image.height
    aspect_ratio = img_width / img_height if img_height > 0 else 0
    if img_width < 200 and img_height < 200:
        return True
    if aspect_ratio > 8:
        return True
    if aspect_ratio < 0.2:
        return True
    if img_width < 150 and img_height < 150:
        return True
    if img_height < 100 and aspect_ratio > 3:
        return True
    if 0.8 <= aspect_ratio <= 1.2 and img_width < 120 and img_height < 120:
        return True
    return False
