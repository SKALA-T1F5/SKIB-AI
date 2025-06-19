import re


# collection 이름 정규화 (모두 소문자로 통일)
def filename_to_collection(name: str) -> str:
    # 특수한 한글 파일명들에 대한 매핑
    special_mappings = {
        "자동차 리포트": "car_report",
        "자동차리포트": "car_report",
    }

    # 특수 매핑 확인
    if name in special_mappings:
        name = special_mappings[name]

    name = name.lower()  # 모두 소문자로 변환
    name = re.sub(r"[^a-z0-9]", "_", name)  # 특수문자, 한글 → _
    name = re.sub(r"_+", "_", name)  # 연속된 _ 정리
    name = name.strip("_")  # 앞뒤 _ 제거

    # 빈 문자열이거나 첫 글자가 알파벳이 아닌 경우 처리
    if not name or not name[0].isalpha():
        name = "c_" + name if name else "collection"

    return name[:50]  # 길이 제한 권장
