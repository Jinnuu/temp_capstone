"""
procurement/utils.py
---
현업 급식 업무용 헬퍼 함수 모음
- calculate_physical_units: 식자재 규격(spec) 문자열을 파싱하여 총 필요량을 포장 단위로 역산출
"""
import re
from decimal import Decimal


def calculate_physical_units(spec_str: str, total_qty_val: float, unit_str: str = "", category: str = "") -> str:
    """
    Ingredient.spec 필드 문자열과 총 필요량을 받아 실제 포장 단위 수량을 반환합니다.

    ▸ 지원 패턴:
      - "5kg", "20kg", "14kg" → 단순 kg 단위 포장 (e.g. 35kg / 5kg = 7통)
      - "5kg / 통", "20kg / 망", "14kg통" → 단위 명칭 포함 포장
      - "70g*10개", "100g*5개", "50g×20개/봉" → 개별 무게 × 개수 per 포장
      - "1kg*10개" → kg 단위 개별 × 개수
      - 기타/미인식 → 총량 + 단위 문자열 그대로 반환

    Args:
        spec_str:      Ingredient.spec 필드값 (e.g. "5kg", "70g*10개", "20kg / 망")
        total_qty_val: 총 필요량 (기본 단위: g 또는 kg, unit_str에 따라 판단)
        unit_str:      Ingredient.unit 필드값 (e.g. "kg", "g")
        category:      Ingredient.category 필드값

    Returns:
        str: 사람이 읽기 쉬운 포장 단위 문자열 (e.g. "7통", "1봉지 (10개)", "3망 (60kg)")
    """
    if not spec_str or not spec_str.strip() or total_qty_val is None:
        qty = round(float(total_qty_val), 2) if total_qty_val else 0
        return f"{qty:g}{unit_str or ''}"

    spec = spec_str.strip()
    total = float(total_qty_val)

    # ─────────────────────────────────────────────────────────────────────────
    # 패턴 A: "Xg × N개[/단위명]" 또는 "Xg * N개" 형식
    # 예: "70g*10개", "100g×5개/봉", "50g * 20개 / 봉지"
    # ─────────────────────────────────────────────────────────────────────────
    pat_a = re.search(
        r"(\d+(?:\.\d+)?)\s*(g|kg|ml|L)\s*[×x\*]\s*(\d+)\s*(?:개|ea|pcs)?(?:\s*/\s*([가-힣a-zA-Z]+))?",
        spec,
        re.IGNORECASE,
    )
    if pat_a:
        piece_qty = float(pat_a.group(1))
        piece_unit = pat_a.group(2).lower()
        pieces_per_pack = int(pat_a.group(3))
        pack_label = pat_a.group(4) or "봉지"

        # 개별 무게를 g 단위로 통일
        if piece_unit == "kg" or piece_unit == "l":
            piece_g = piece_qty * 1000
        elif piece_unit == "ml":
            piece_g = piece_qty  # mL ≈ g 근사
        else:
            piece_g = piece_qty

        pack_g = piece_g * pieces_per_pack  # 포장 1개의 총 무게(g)

        # total을 g 단위로 환산
        if unit_str.lower() == "kg":
            total_g = total * 1000
        else:
            total_g = total

        if pack_g <= 0:
            return f"{total:g}{unit_str or ''}"

        packs = total_g / pack_g
        packs_ceil = int(packs) if packs == int(packs) else int(packs) + 1

        # 총 개수 계산
        total_pieces = packs_ceil * pieces_per_pack

        return f"{packs_ceil}{pack_label} ({total_pieces}개)"

    # ─────────────────────────────────────────────────────────────────────────
    # 패턴 B: "Xkg × N개" 또는 "Xkg*N" 형식
    # 예: "1kg*10개", "2kg × 5ea"
    # ─────────────────────────────────────────────────────────────────────────
    pat_b = re.search(
        r"(\d+(?:\.\d+)?)\s*kg\s*[×x\*]\s*(\d+)\s*(?:개|ea|pcs)?(?:\s*/\s*([가-힣a-zA-Z]+))?",
        spec,
        re.IGNORECASE,
    )
    if pat_b:
        kg_per_piece = float(pat_b.group(1))
        pieces_per_pack = int(pat_b.group(2))
        pack_label = pat_b.group(3) or "박스"
        pack_kg = kg_per_piece * pieces_per_pack

        if unit_str.lower() == "g":
            total_kg = total / 1000
        else:
            total_kg = total

        if pack_kg <= 0:
            return f"{total:g}{unit_str or ''}"

        packs = total_kg / pack_kg
        packs_ceil = int(packs) if packs == int(packs) else int(packs) + 1
        return f"{packs_ceil}{pack_label} ({packs_ceil * pieces_per_pack}개)"

    # ─────────────────────────────────────────────────────────────────────────
    # 패턴 C: "Xkg / 단위명" 또는 "Xkg단위명" 형식
    # 예: "5kg / 통", "20kg / 망", "14kg통", "10kg/포"
    # ─────────────────────────────────────────────────────────────────────────
    pat_c = re.search(
        r"(\d+(?:\.\d+)?)\s*kg\s*(?:/\s*)?([가-힣a-zA-Z]+)?",
        spec,
        re.IGNORECASE,
    )
    if pat_c:
        pkg_kg = float(pat_c.group(1))
        pkg_label = pat_c.group(2) or "통"
        # 흔한 단위 정교화
        if pkg_label.lower() in ("kg", "킬로", ""):
            pkg_label = "통"

        if unit_str.lower() == "g":
            total_kg = total / 1000
        else:
            total_kg = total

        if pkg_kg <= 0:
            return f"{total:g}kg"

        pkgs = total_kg / pkg_kg
        pkgs_ceil = int(pkgs) if pkgs == int(pkgs) else int(pkgs) + 1
        total_display = round(pkgs_ceil * pkg_kg, 2)

        if total_display == int(total_display):
            total_display = int(total_display)

        return f"{pkgs_ceil}{pkg_label} ({total_display}kg)"

    # ─────────────────────────────────────────────────────────────────────────
    # 패턴 D: 단순 수량(개수, 봉, 포 등) 숫자만 있는 경우
    # 예: "10개", "5봉"
    # ─────────────────────────────────────────────────────────────────────────
    pat_d = re.search(r"(\d+(?:\.\d+)?)\s*([가-힣]+)", spec)
    if pat_d:
        pkg_cnt = float(pat_d.group(1))
        pkg_label = pat_d.group(2)
        if pkg_cnt <= 0:
            return f"{total:g}{unit_str or ''}"
        pkgs = total / pkg_cnt
        pkgs_ceil = int(pkgs) if pkgs == int(pkgs) else int(pkgs) + 1
        return f"{pkgs_ceil}{pkg_label}"

    # ─────────────────────────────────────────────────────────────────────────
    # 폴백: 파싱 불가 → 총량 + 단위 그대로
    # ─────────────────────────────────────────────────────────────────────────
    qty = round(total, 2)
    if qty == int(qty):
        qty = int(qty)
    return f"{qty}{unit_str or ''}"


def parse_spec_unit_and_qty(spec_str: str, total_qty_val: float, unit_str: str = "", category: str = ""):
    """
    Ingredient.spec 문자열과 총 필요량을 분석하여 (환산 수량, 환산 단위) 튜플을 반환합니다.

    Returns:
        tuple[float, str]: (환산 수량, 환산 단위 문자열)
    """
    if total_qty_val is None:
        total_qty_val = 0.0

    total = float(total_qty_val)
    unit_norm = (unit_str or "").strip()
    cat_norm = (category or "").strip()

    if not spec_str or not spec_str.strip():
        if ("쌀" in cat_norm or "김치" in cat_norm) and unit_norm.lower() in ["g", "그램"]:
            val = round(total / 1000.0, 1)
            return (int(val) if val == int(val) else val), "kg"
        val = round(total, 1)
        return (int(val) if val == int(val) else val), unit_norm or "kg"

    spec = spec_str.strip()

    # Pattern A: "70g*10개", "100g×5개/봉"
    pat_a = re.search(
        r"(\d+(?:\.\d+)?)\s*(g|kg|ml|L)\s*[×x\*]\s*(\d+)\s*(?:개|ea|pcs)?(?:\s*/\s*([가-힣a-zA-Z]+))?",
        spec,
        re.IGNORECASE,
    )
    if pat_a:
        piece_qty = float(pat_a.group(1))
        piece_unit = pat_a.group(2).lower()
        pieces_per_pack = int(pat_a.group(3))
        pack_label = pat_a.group(4) or "봉"

        if piece_unit in ["kg", "l"]:
            piece_g = piece_qty * 1000.0
        elif piece_unit == "ml":
            piece_g = piece_qty
        else:
            piece_g = piece_qty

        pack_g = piece_g * pieces_per_pack

        if unit_norm.lower() == "kg":
            total_g = total * 1000.0
        else:
            total_g = total

        if pack_g > 0:
            packs = round(total_g / pack_g, 1)
            val = int(packs) if packs == int(packs) else packs
            return val, pack_label

    # Pattern B: "1kg*10개", "2kg × 5ea"
    pat_b = re.search(
        r"(\d+(?:\.\d+)?)\s*kg\s*[×x\*]\s*(\d+)\s*(?:개|ea|pcs)?(?:\s*/\s*([가-힣a-zA-Z]+))?",
        spec,
        re.IGNORECASE,
    )
    if pat_b:
        kg_per_piece = float(pat_b.group(1))
        pieces_per_pack = int(pat_b.group(2))
        pack_label = pat_b.group(3) or "박스"
        pack_kg = kg_per_piece * pieces_per_pack

        if unit_norm.lower() == "g":
            total_kg = total / 1000.0
        else:
            total_kg = total

        if pack_kg > 0:
            packs = round(total_kg / pack_kg, 1)
            val = int(packs) if packs == int(packs) else packs
            return val, pack_label

    # Pattern C: "20kg / 망", "5kg / 통", "14kg통", "10kg/포"
    pat_c = re.search(
        r"(\d+(?:\.\d+)?)\s*kg\s*(?:/\s*)?([가-힣a-zA-Z]+)?",
        spec,
        re.IGNORECASE,
    )
    if pat_c:
        pkg_kg = float(pat_c.group(1))
        pkg_label = pat_c.group(2) or "통"
        if pkg_label.lower() in ("kg", "킬로", ""):
            pkg_label = "통"

        if unit_norm.lower() == "g":
            total_kg = total / 1000.0
        else:
            total_kg = total

        if pkg_kg > 0:
            pkgs = round(total_kg / pkg_kg, 1)
            val = int(pkgs) if pkgs == int(pkgs) else pkgs
            return val, pkg_label

    # Pattern D: "10개", "5봉"
    pat_d = re.search(r"(\d+(?:\.\d+)?)\s*([가-힣]+)", spec)
    if pat_d:
        pkg_cnt = float(pat_d.group(1))
        pkg_label = pat_d.group(2)
        if pkg_cnt > 0:
            pkgs = round(total / pkg_cnt, 1)
            val = int(pkgs) if pkgs == int(pkgs) else pkgs
            return val, pkg_label

    # Fallback
    if ("쌀" in cat_norm or "김치" in cat_norm) and unit_norm.lower() in ["g", "그램"]:
        val = round(total / 1000.0, 1)
        return (int(val) if val == int(val) else val), "kg"

    val = round(total, 1)
    return (int(val) if val == int(val) else val), unit_norm or "kg"


def format_qty(val: float) -> str:
    """숫자를 소수점 불필요 시 정수, 필요 시 최대 2자리 소수점으로 포맷"""
    if val == int(val):
        return str(int(val))
    return str(round(val, 2))

