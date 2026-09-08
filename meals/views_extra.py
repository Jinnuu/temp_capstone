import csv
import io
import re
from datetime import date, datetime
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from openpyxl import load_workbook

from .models import DietMenu, DietPlan, Menu


def monthly_mealplan_create(request):
    if request.method == "POST":
        messages.info(
            request,
            "월간 식단 등록 저장 로직은 추후 연결 예정입니다. 현재는 화면 미리보기 단계입니다.",
        )
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

                cell_str = str(cell_val).strip()
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
    if request.method == "POST":
        # 1. 파일 존재 여부 확인
        if not request.FILES:
            messages.error(request, "업로드할 엑셀 파일을 선택해주세요.")
            return redirect(request.path)
        
        # 폼에서 파일 가져오기 (input name과 무관하게 첫 번째 파일 강제 추출)
        excel_file = list(request.FILES.values())[0]
        
        try:
            wb = load_workbook(excel_file, data_only=True)
            ws = wb.active
            
            date_row_index = -1
            date_map = {} # {열 인덱스: 날짜 객체}
            
            # 2. 날짜 행 찾기 (정규식: 마침표, 하이픈, 슬래시 모두 지원)
            for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
                for col_idx, cell in enumerate(row):
                    cell_str = str(cell).strip()
                    
                    # 숫자[-/.]숫자 패턴이 발견되면 날짜로 인식
                    if cell and re.search(r'\d{1,2}[-/\.]\d{1,2}', cell_str):
                        date_row_index = row_idx
                        
                        # 월, 일 추출
                        match = re.search(r'(\d{1,2})[-/\.](\d{1,2})', cell_str)
                        if match:
                            month, day = int(match.group(1)), int(match.group(2))
                            
                            # 연도 추출 (없으면 올해 연도 적용)
                            year_match = re.search(r'(\d{4})[-/\.]', cell_str)
                            year = int(year_match.group(1)) if year_match else date.today().year
                            
                            try:
                                date_map[col_idx] = date(year, month, day)
                            except ValueError:
                                pass
                                
                if date_map: # 날짜를 하나라도 찾았으면 행 탐색 종료
                    break
                    
            if not date_map:
                messages.error(request, "엑셀에서 날짜(08-10 또는 08.24) 형식을 찾을 수 없습니다.")
                return redirect(request.path)

            # 3. 끼니별 메뉴 추출 및 줄바꿈 처리
            current_meal_type = None
            valid_meal_types = ["조식", "중식", "석식"]
            
            # 날짜 행 바로 아래부터 끝까지 탐색
            for row in ws.iter_rows(min_row=date_row_index + 2, values_only=True):
                first_cell = str(row[0]).strip() if row[0] else ""
                
                if first_cell in valid_meal_types:
                    current_meal_type = first_cell
                elif first_cell == "비고":
                    current_meal_type = None # 비고부터는 무시
                    
                if not current_meal_type:
                    continue
                    
                # 날짜가 있는 열만 매핑
                for col_idx, target_date in date_map.items():
                    cell_val = row[col_idx]
                    if not cell_val:
                        continue
                        
                    # 엑셀의 줄바꿈(Alt+Enter) 데이터 분리 및 찌꺼기(_x000D_) 제거
                    raw_text = str(cell_val).replace("_x000D_", "").replace("\r", "")
                    split_menus = [m.strip() for m in raw_text.split('\n') if m.strip()]
                    
                    if not split_menus:
                        continue
                        
                    plan, _ = DietPlan.objects.get_or_create(
                        target_date=target_date,
                        meal_type=current_meal_type
                    )
                    
                    for menu_name in split_menus:
                        # 하단 안내 문구 등 가비지 텍스트 필터링
                        if any(kw in menu_name for kw in ["물품수급", "변경될 수", "비고", "조식", "중식", "석식"]):
                            continue
                            
                        menu_obj, _ = Menu.objects.get_or_create(
                            name=menu_name,
                            defaults={'category': '기타'}
                        )
                        DietMenu.objects.get_or_create(
                            diet_plan=plan,
                            menu=menu_obj
                        )
                        
            messages.success(request, "엑셀 식단이 성공적으로 등록되었습니다!")
            return redirect('meals:mealplan_list')
            
        except Exception as e:
            messages.error(request, f"파일 파싱 중 오류가 발생했습니다: {str(e)}")
            return redirect(request.path)

    # GET 요청: 업로드 화면 렌더링
    return render(request, 'meals/mealplan_bulk_upload.html')

