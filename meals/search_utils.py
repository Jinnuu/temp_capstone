from difflib import SequenceMatcher
import re


HANGUL_RE = re.compile(r"[가-힣]")
ALNUM_RE = re.compile(r"[a-z0-9]")


def normalize_text(value):
    """검색 비교용 문자열 정규화."""
    return (value or "").strip().lower().replace(" ", "")


def has_hangul(value):
    return bool(HANGUL_RE.search(value or ""))


def has_alnum(value):
    return bool(ALNUM_RE.search(value or ""))


def same_script_family(query, name):
    """영문 입력이 한글 메뉴를 잡거나, 한글 입력이 영문 테스트 메뉴를 잡는 것을 방지."""
    q_has_hangul = has_hangul(query)
    n_has_hangul = has_hangul(name)
    q_has_alnum = has_alnum(query)
    n_has_alnum = has_alnum(name)

    if q_has_hangul and n_has_alnum and not n_has_hangul:
        return False

    if q_has_alnum and n_has_hangul and not q_has_hangul:
        return False

    return True


def similarity(a, b):
    a = normalize_text(a)
    b = normalize_text(b)

    if not a or not b:
        return 0.0

    return SequenceMatcher(None, a, b).ratio()


def is_rice_like(query, name):
    """밥류 메뉴를 묶기 위한 최소 규칙.

    예:
    - 쌀밥 검색 → 쌀밥, 흰밥, 잡곡밥, 현미밥 등
    - 살밥 검색 → 쌀밥도 유사 후보
    """
    q = normalize_text(query)
    n = normalize_text(name)

    if not has_hangul(q) or not has_hangul(n):
        return False

    rice_query_keywords = ["밥", "쌀", "백미", "흰밥", "현미", "잡곡", "공기밥"]
    rice_name_keywords = ["밥", "쌀", "백미", "흰밥", "현미", "잡곡", "공기밥"]

    if not any(keyword in q for keyword in rice_query_keywords):
        return False

    return any(keyword in n for keyword in rice_name_keywords)


def score_menu(menu, query):
    """메뉴명 검색 점수 계산.

    의도:
    - 사용자가 dd를 입력하는 중 d만 입력한 상태에서도 dd는 후보로 표시
    - 그러나 d 때문에 밥/쌀밥/국물 같은 한글 메뉴가 뜨지는 않게 함
    - 쌀밥 검색 시 밥류 메뉴 중심 표시
    - 살밥처럼 한 글자 오타가 있어도 쌀밥 표시
    """
    q = normalize_text(query)
    name = normalize_text(getattr(menu, "name", ""))
    category = normalize_text(getattr(menu, "category", ""))

    if not q or not name:
        return 0.0

    if not same_script_family(q, name):
        return 0.0

    # 1. 완전 일치
    if q == name:
        return 1.0

    # 2. 포함 관계
    # 사용자가 dd를 입력하는 과정에서 d를 입력했을 때 dd가 떠야 하므로 유지.
    if q in name:
        # 너무 짧은 검색어는 포함 검색만 허용하고, fuzzy/semantic으로 확장하지 않는다.
        return 0.94 if len(q) >= 2 else 0.82

    if name in q:
        return 0.88

    # 3. 카테고리 완전 일치
    if category and q == category:
        return 0.76

    # 4. 한 글자 검색어는 여기서 중단.
    # 예: d → dd는 위 포함 관계에서 이미 잡힘.
    # 하지만 d → test, d → 밥 같은 확장은 막는다.
    if len(q) <= 1:
        return 0.0

    # 5. 밥류 의미 보정
    if is_rice_like(q, name):
        return 0.68

    # 6. 오타 보정
    sim = similarity(q, name)

    if has_hangul(q):
        # 한글 메뉴명은 짧으므로 너무 높게 잡으면 '살밥 → 쌀밥'이 안 잡힌다.
        return sim if sim >= 0.62 else 0.0

    # 영문/숫자 검색은 test/dd 같은 테스트 메뉴가 많으므로 더 엄격하게.
    return sim if sim >= 0.78 else 0.0


def fuzzy_menu_results(menus, query, limit=12):
    q = normalize_text(query)

    if not q:
        return []

    scored = []

    for menu in menus:
        score = score_menu(menu, q)

        if score > 0:
            scored.append((score, menu))

    scored.sort(key=lambda item: (-item[0], getattr(item[1], "name", "")))

    return [
        {
            "id": menu.id,
            "name": menu.name,
            "category": getattr(menu, "category", "") or "",
            "score": round(score, 4),
        }
        for score, menu in scored[:limit]
    ]
