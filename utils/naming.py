import re
import unicodedata
from pathlib import Path


# collection 이름 정규화 (모두 소문자로 통일)
def filename_to_collection(document_name: str) -> str:
    """
    문서명을 ChromaDB collection 이름으로 정규화

    ChromaDB collection 이름 규칙:
    - 3-63자 길이
    - 영문 소문자, 숫자, 하이픈(-), 언더스코어(_)만 허용
    - 영문자로 시작해야 함
    - 하이픈이나 점으로 끝날 수 없음

    Args:
        document_name: 원본 문서명 (파일명 포함 가능)

    Returns:
        str: 정규화된 collection 이름
    """
    if not document_name:
        return "document_collection"

    # 파일 확장자 제거
    name = Path(document_name).stem

    # 유니코드 정규화 (한글 등 → 영문)
    name = unicodedata.normalize("NFKD", name)

    # 한글 → 영문 변환 (간단한 로마자 변환)
    name = _korean_to_roman(name)

    # 소문자 변환
    name = name.lower()

    # 허용되지 않는 문자를 언더스코어로 변환
    name = re.sub(r"[^a-z0-9_-]", "_", name)

    # 연속된 언더스코어/하이픈 정리
    name = re.sub(r"[_-]+", "_", name)

    # 앞뒤 언더스코어/하이픈 제거
    name = name.strip("_-")

    # 숫자로 시작하는 경우 앞에 prefix 추가
    if name and name[0].isdigit():
        name = f"doc_{name}"

    # 영문자로 시작하지 않는 경우 prefix 추가
    if not name or not name[0].isalpha():
        name = f"doc_{name}" if name else "document"

    # 길이 제한 (3-63자)
    if len(name) < 3:
        name = f"{name}_collection"[:63]
    elif len(name) > 63:
        name = name[:60] + "_" + str(hash(document_name) % 100)
        name = name[:63]

    return name


def _korean_to_roman(text: str) -> str:
    """
    한글을 간단한 로마자로 변환

    Args:
        text: 한글이 포함된 텍스트

    Returns:
        str: 로마자로 변환된 텍스트
    """
    # 한글 단어별 매핑 (더 의미있는 변환)
    korean_word_map = {
        "문서": "document",
        "보고서": "report",
        "분석": "analysis",
        "데이터": "data",
        "학습": "learning",
        "연구": "research",
        "결과": "result",
        "사용자": "user",
        "매뉴얼": "manual",
        "한글": "hangul",
        "테스트": "test",
        "시험": "exam",
        "프로젝트": "project",
        "개발": "development",
        "설계": "design",
        "구현": "implementation",
        "시스템": "system",
        "관리": "management",
    }

    # 단어 단위로 먼저 변환 시도
    for korean, english in korean_word_map.items():
        text = text.replace(korean, english)

    # 남은 한글 문자 처리
    korean_char_map = {
        "ㄱ": "g",
        "ㄴ": "n",
        "ㄷ": "d",
        "ㄹ": "r",
        "ㅁ": "m",
        "ㅂ": "b",
        "ㅅ": "s",
        "ㅇ": "",
        "ㅈ": "j",
        "ㅊ": "ch",
        "ㅋ": "k",
        "ㅌ": "t",
        "ㅍ": "p",
        "ㅎ": "h",
        "ㅏ": "a",
        "ㅑ": "ya",
        "ㅓ": "eo",
        "ㅕ": "yeo",
        "ㅗ": "o",
        "ㅛ": "yo",
        "ㅜ": "u",
        "ㅠ": "yu",
        "ㅡ": "eu",
        "ㅣ": "i",
        "ㅐ": "ae",
        "ㅒ": "yae",
        "ㅔ": "e",
        "ㅖ": "ye",
    }

    result = []
    for char in text:
        if "가" <= char <= "힣":
            # 한글 완성형을 간단하게 처리
            try:
                code = ord(char) - ord("가")
                jong = code % 28
                jung = (code - jong) // 28 % 21
                cho = ((code - jong) // 28 - jung) // 21

                cho_list = [
                    "ㄱ",
                    "ㄲ",
                    "ㄴ",
                    "ㄷ",
                    "ㄸ",
                    "ㄹ",
                    "ㅁ",
                    "ㅂ",
                    "ㅃ",
                    "ㅅ",
                    "ㅆ",
                    "ㅇ",
                    "ㅈ",
                    "ㅉ",
                    "ㅊ",
                    "ㅋ",
                    "ㅌ",
                    "ㅍ",
                    "ㅎ",
                ]
                jung_list = [
                    "ㅏ",
                    "ㅐ",
                    "ㅑ",
                    "ㅒ",
                    "ㅓ",
                    "ㅔ",
                    "ㅕ",
                    "ㅖ",
                    "ㅗ",
                    "ㅘ",
                    "ㅙ",
                    "ㅚ",
                    "ㅛ",
                    "ㅜ",
                    "ㅝ",
                    "ㅞ",
                    "ㅟ",
                    "ㅠ",
                    "ㅡ",
                    "ㅢ",
                    "ㅣ",
                ]

                cho_char = cho_list[cho] if cho < len(cho_list) else "g"
                jung_char = jung_list[jung] if jung < len(jung_list) else "a"

                roman = korean_char_map.get(cho_char, cho_char) + korean_char_map.get(
                    jung_char, jung_char
                )
                result.append(roman)
            except:
                result.append("han")
        elif char in korean_char_map:
            result.append(korean_char_map[char])
        else:
            result.append(char)

    return "".join(result)
