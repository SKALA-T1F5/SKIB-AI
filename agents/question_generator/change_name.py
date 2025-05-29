import re


# collection 이름 정규화
def normalize_collection_name(name: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9]", "_", name)  # 특수문자, 한글 → _
    name = re.sub(r"_+", "_", name)  # 연속된 _ 정리
    name = name.strip("_")  # 앞뒤 _ 제거
    if not name or not name[0].isalpha():  # 첫 글자 알파벳 보장
        name = "C_" + name
    return name[:50]  # 길이 제한 권장
