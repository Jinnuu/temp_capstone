
import csv
import io
import re
from datetime import datetime, date

import openpyxl
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render

from .models import DietMenu, DietPlan, Menu

MEAL_LABELS = {
    "조식": "조식",
    "breakfast": "조식",
    "아침": "조식",
    "중식": "중식",
    "lunch": "중식",
    "점심": "중식",
    "석식": "석식",
    "dinner": "석식",
    "저녁": "석식",
}


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def _compact(value):
    return _clean(value).replace(" ", "").lower()


def _parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _clean(value)
    for fmt in ["%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d"]:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _parse_int(value, default=0):
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return default


def _split_menus(value):
    text = _clean(value)
    if not text:
        return []
    for sep in ["/", "|", "\n", ";"]:
        text = text.replace(sep, ",")
    return [item.strip() for item in text.split(",") if item.strip()]


def _meal_type(value):
    return MEAL_LABELS.get(_compact(value), MEAL_LABELS.get(_clean(value), ""))


def _read_upload_rows(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith(".csv"):
        raw = uploaded_file.read()
        for enc in ["utf-8-sig", "cp949", "euc-kr"]:
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)

    workbook = openpyxl.load_workbook(uploaded_file, data_only=True)
    sheet = workbook.active

    # 상단 안내문이 있어도 헤더를 찾는다.
    header_row = None
    headers = []
    for r in range(1, min(sheet.max_row, 20) + 1):
        values = [_clean(sheet.cell(r, c).value) for c in range(1, sheet.max_column + 1)]
        compact = [_compact(v) for v in values]
        if any(v in compact for v in ["날짜", "일자", "date"]) and (
            any(v in compact for v in ["끼니", "mealtype", "meal_type"]) or any(v in compact for v in ["조식", "중식", "석식"])
        ):
            header_row = r
            headers = values
            break
    if header_row is None:
        records = parse_grid_excel(sheet)
        if records:
            return [{"date": row["target_date"], "meal_type": row["meal_type"],
                     "menu_name": row["menu_name"]} for row in records]
        header_row = 1
        headers = [_clean(sheet.cell(1, c).value) for c in range(1, sheet.max_column + 1)]

    rows = []
    for r in range(header_row + 1, sheet.max_row + 1):
        row = {}
        empty = True
        for c, h in enumerate(headers, start=1):
            if not h:
                continue
            value = sheet.cell(r, c).value
            if value not in [None, ""]:
                empty = False
            row[h] = value
        if not empty:
            rows.append(row)
    return rows


def _find(row, aliases):
    compact_map = {_compact(k): v for k, v in row.items()}
    for alias in aliases:
        key = _compact(alias)
        if key in compact_map:
            return compact_map[key]
    return None


def _collect_mealplan_rows(rows):
    """두 가지 형식 모두 지원.

    1) 행 단위: 날짜 / 끼니 / 메뉴명 / 기준식수
    2) 주간형: 날짜 / 조식 / 중식 / 석식 / 기준식수_조식 ...
    """
    grouped = {}
    skipped = []
    for idx, row in enumerate(rows, start=2):
        target_date = _parse_date(_find(row, ["날짜", "일자", "date", "식단일"]))
        if not target_date:
            skipped.append({"row": idx, "reason": "날짜를 읽을 수 없음"})
            continue

        meal = _meal_type(_find(row, ["끼니", "meal_type", "mealtype", "구분"]))
        menu_name = _find(row, ["메뉴명", "메뉴", "menu", "menu_name", "음식명"])
        headcount = _parse_int(_find(row, ["기준식수", "식수", "headcount", "인원"]), 0)

        if meal and menu_name:
            key = (target_date, meal)
            grouped.setdefault(key, {"headcount": headcount, "menus": []})
            grouped[key]["headcount"] = headcount or grouped[key]["headcount"]
            grouped[key]["menus"].extend(_split_menus(menu_name))
            continue

        # wide format
        found_any = False
        for label in ["조식", "중식", "석식"]:
            menus = _split_menus(_find(row, [label]))
            if not menus:
                continue
            found_any = True
            hc = _parse_int(_find(row, [f"기준식수_{label}", f"{label}식수", f"식수_{label}"]), 0)
            key = (target_date, label)
            grouped.setdefault(key, {"headcount": hc, "menus": []})
            grouped[key]["headcount"] = hc or grouped[key]["headcount"]
            grouped[key]["menus"].extend(menus)
        if not found_any:
            skipped.append({"row": idx, "reason": "끼니/메뉴 정보를 찾을 수 없음"})
    return grouped, skipped


@transaction.atomic
def _save_grouped_mealplans(grouped):
    plan_count = 0
    menu_count = 0
    for (target_date, meal_type), payload in grouped.items():
        plan, _ = DietPlan.objects.update_or_create(
            target_date=target_date,
            meal_type=meal_type,
            defaults={"headcount": payload.get("headcount") or 0},
        )
        DietMenu.objects.filter(diet_plan=plan).delete()
        seen = set()
        for menu_name in sorted(payload.get("menus", []), key=lambda name: get_menu_priority_and_category(name)[0]):
            clean_name = _clean(menu_name)
            if not clean_name or clean_name in seen:
                continue
            seen.add(clean_name)
            menu, _ = Menu.objects.get_or_create(name=clean_name, defaults={"category": get_menu_priority_and_category(clean_name)[1]})
            DietMenu.objects.get_or_create(diet_plan=plan, menu=menu)
            menu_count += 1
        plan_count += 1
    return plan_count, menu_count


def monthly_mealplan_create(request):
    if request.method == "POST" and request.FILES.get("mealplan_file"):
        return mealplan_bulk_upload(request)
    if request.method == "POST":
        messages.info(request, "월간 식단은 엑셀 업로드 또는 주/일간 식단 등록 화면에서 입력해 주세요.")
        return redirect("meals:mealplan_list")
    return render(request, "meals/monthly_mealplan_create.html")


def parse_date_val(date_val):
    if isinstance(date_val, datetime):
        return date_val.date()
    if isinstance(date_val, date):
        return date_val

    if not date_val:
        return None

    date_str = str(date_val).strip()
    # Try direct ISO/Dot/Slash formats
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    # Regex pattern matching
    # Pattern 1: YYYY-MM-DD, YYYY.MM.DD, YYYY/MM/DD
    m = re.search(r"(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})", date_str)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # Pattern 2: YYYY년 MM월 DD일
    m = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", date_str)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass

    # Pattern 3: MM-DD, MM.DD, MM/DD (e.g. 08-10(월), 05/20)
    m = re.search(r"(\d{1,2})[./\-](\d{1,2})", date_str)
    if m:
        try:
            current_year = date.today().year
            return date(current_year, int(m.group(1)), int(m.group(2)))
        except ValueError:
            pass

    # Pattern 4: MM월 DD일 (e.g. 08월 10일(월))
    m = re.search(r"(\d{1,2})월\s*(\d{1,2})일", date_str)
    if m:
        try:
            current_year = date.today().year
            return date(current_year, int(m.group(1)), int(m.group(2)))
        except ValueError:
            pass

    return None


def detect_meal_type_from_text(text):
    if not text:
        return None
    s = str(text).strip()
    if "조식" in s or "아침" in s:
        return "조식"
    if "중식" in s or "점심" in s:
        return "중식"
    if "석식" in s or "저녁" in s:
        return "석식"
    if "기타" in s or "간식" in s:
        return "기타"
    return None


def get_menu_priority_and_category(menu_name):
    """
    Returns (priority_int, category_name) based on keyword matching:
    1순위: 밥/주식 (밥, 죽, 면, 국수, 크로와상, 주먹밥 등)
    2순위: 국물류 (국, 찌개, 탕, 전골, 스프, 우동, 수제비 등)
    3순위: 주반찬/단백질 (볶음, 조림, 찜, 구이, 튀김, 전, 까스, 고기, 닭, 오리, 스테이크, 제육, 두루치기, 함박, 돈육 등)
    4순위: 부반찬/채소 (무침, 나물, 김치, 깍두기, 석박지, 단무지, 피클, 샐러드, 콩자반, 젓, 채 등)
    5순위: 과일/간식 (사과, 바나나, 과일, 빵, 케이크, 쿠키, 요구르트, 요거트, 푸딩, 시리얼, 후레이크 등)
    6순위: 음료 (우유, 주스, 차, 라떼, 음료, 에이드, 두유 등)
    7순위: 기타
    """
    name = str(menu_name).strip()

    # 1. 밥/주식
    cat1_keywords = ["밥", "죽", "면", "국수", "크로와상", "주먹밥", "필라프", "리조또", "스파게티", "파스타", "짜장", "짬뽕"]
    for kw in cat1_keywords:
        if kw in name:
            return (1, "밥/주식")

    # 2. 국물류
    cat2_keywords = ["국", "찌개", "탕", "전골", "스프", "우동", "수제비", "오뎅국", "장국"]
    for kw in cat2_keywords:
        if kw in name:
            return (2, "국물류")

    # 3. 주반찬/단백질
    cat3_keywords = [
        "볶음",
        "조림",
        "찜",
        "구이",
        "튀김",
        "전",
        "까스",
        "고기",
        "닭",
        "오리",
        "스테이크",
        "제육",
        "두루치기",
        "함박",
        "돈육",
        "불고기",
        "탕수육",
        "너겟",
        "소시지",
        "햄",
        "동그랑땡",
    ]
    for kw in cat3_keywords:
        if kw in name:
            return (3, "주반찬")

    # 4. 부반찬/채소
    cat4_keywords = [
        "무침",
        "나물",
        "김치",
        "깍두기",
        "석박지",
        "단무지",
        "피클",
        "샐러드",
        "콩자반",
        "젓",
        "채",
        "겉절이",
        "지",
    ]
    for kw in cat4_keywords:
        if kw in name:
            return (4, "부반찬")

    # 5. 과일/간식
    cat5_keywords = [
        "사과",
        "바나나",
        "과일",
        "빵",
        "케이크",
        "쿠키",
        "요구르트",
        "요거트",
        "푸딩",
        "시리얼",
        "후레이크",
        "떡",
        "와플",
        "도넛",
    ]
    for kw in cat5_keywords:
        if kw in name:
            return (5, "과일/간식")

    # 6. 음료
    cat6_keywords = ["우유", "주스", "차", "라떼", "음료", "에이드", "두유", "식혜", "수정과", "쥬스"]
    for kw in cat6_keywords:
        if kw in name:
            return (6, "음료")

    # 7. 기타
    return (7, "기타")


EXCLUDE_KEYWORDS = [
    "비고",
    "원산지",
    "물품수급",
    "알레르기",
    "변경",
    "사정에 따라",
    "참고",
    "안내",
    "영양사",
    "조리사",
    "칼로리",
    "kcal",
    "Kcal",
    "위 식단",
    "식단표",
    "주간식단",
    "월간식단",
    "구분",
    "식단",
    "요일",
    "열량",
    "단백질",
]


def is_notice_or_noise(text):
    if not text:
        return True
    s = str(text).strip()
    if not s:
        return True

    # Notice disclaimers and long sentences are ignored
    if len(s) > 25:
        return True

    for kw in EXCLUDE_KEYWORDS:
        if kw in s:
            return True

    return False


def parse_grid_excel(ws):
    """
    Parses calendar/grid layout Excel sheets where dates are across columns
    and meal types (조식, 중식, 석식) segment rows.
    """
    all_rows = list(ws.iter_rows(values_only=True))
    if not all_rows:
        return []

    # 1. Locate the best date header row (the row with maximum valid date columns)
    best_date_row_idx = None
    best_col_date_map = {}  # col_idx -> date

    for r_idx, row in enumerate(all_rows):
        temp_date_map = {}
        for c_idx, cell_val in enumerate(row):
            if cell_val is None:
                continue
            parsed_d = parse_date_val(cell_val)
            if parsed_d:
                temp_date_map[c_idx] = parsed_d

        # Pick the row that contains the most date columns
        if len(temp_date_map) > len(best_col_date_map):
            best_col_date_map = temp_date_map
            best_date_row_idx = r_idx

    if best_date_row_idx is None or not best_col_date_map:
        return []

    parsed_records = []
    current_meal_type = "중식"  # Default fallback

    # 2. Iterate rows below date header row
    for r_idx in range(best_date_row_idx + 1, len(all_rows)):
        row = all_rows[r_idx]
        if not row:
            continue

        # Convert row values to strings for row-level notice checks
        row_str_concat = " ".join(str(cell) for cell in row if cell is not None).strip()

        # Stop scanning if encountering bottom notice blocks or disclaimers at row start
        if any(kw in row_str_concat for kw in ["원산지 표시", "※", "* 위 식단", "영양사 :", "조리사 :"]):
            # If line is clearly a bottom disclaimer banner, stop reading further
            if "※" in row_str_concat or "사정에 따라" in row_str_concat or "원산지" in row_str_concat:
                break

        # Check if row contains a meal type label
        detected_meal = None
        for cell_val in row:
            if cell_val is not None:
                m_type = detect_meal_type_from_text(cell_val)
                if m_type:
                    detected_meal = m_type
                    break

        if detected_meal:
            current_meal_type = detected_meal

        # 3. Extract menu text for each mapped date column across row
        for col_idx, target_date in best_col_date_map.items():
            if col_idx < len(row):
                cell_val = row[col_idx]
                if cell_val is None:
                    continue

                cell_str = str(cell_val).replace("_x000D_", "").strip()
                if not cell_str or cell_str in ("-", "N/A", "없음", "휴무", "공휴일"):
                    continue

                # Filter out notice text, long disclaimers, or noise
                if is_notice_or_noise(cell_str):
                    continue

                # Skip if cell value itself is a date or meal type label
                if parse_date_val(cell_str) or detect_meal_type_from_text(cell_str) == cell_str:
                    continue

                # Split menu items by newline, comma, slash
                items = re.split(r"[\n\r,/]+", cell_str)
                for item in items:
                    menu_name = item.strip()
                    if menu_name and not is_notice_or_noise(menu_name):
                        parsed_records.append(
                            {
                                "target_date": target_date,
                                "meal_type": current_meal_type,
                                "menu_name": menu_name,
                                "category": "기타",
                            }
                        )

    return parsed_records
def mealplan_bulk_upload(request):
    if request.method == "GET":
        return render(request, "meals/mealplan_bulk_upload.html")

    uploaded_file = request.FILES.get("mealplan_file") or request.FILES.get("file")
    if not uploaded_file:
        messages.error(request, "CSV 또는 XLSX 파일을 선택해 주세요.")
        return redirect("meals:mealplan_bulk_upload")
    if not uploaded_file.name.lower().endswith((".xlsx", ".xlsm", ".xltx", ".csv")):
        messages.error(request, "현재는 .xlsx, .xlsm, .xltx, .csv 파일만 지원합니다.")
        return redirect("meals:mealplan_bulk_upload")

    try:
        rows = _read_upload_rows(uploaded_file)
        grouped, skipped = _collect_mealplan_rows(rows)
        if not grouped:
            messages.error(request, "저장할 식단 데이터를 찾지 못했습니다. 날짜/끼니/메뉴명 컬럼을 확인해 주세요.")
            return redirect("meals:mealplan_bulk_upload")
        plan_count, menu_count = _save_grouped_mealplans(grouped)
        if skipped:
            messages.warning(request, f"일부 행 {len(skipped)}건은 제외되었습니다.")
        messages.success(request, f"식단 엑셀 업로드 완료: 식단 {plan_count}건, 메뉴 연결 {menu_count}건 반영")
        return redirect("meals:mealplan_list")
    except Exception as exc:
        messages.error(request, f"식단 엑셀 업로드 중 오류가 발생했습니다: {exc}")
        return redirect("meals:mealplan_bulk_upload")
