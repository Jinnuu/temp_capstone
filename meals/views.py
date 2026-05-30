import calendar
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import pandas as pd
from .models import Menu,Recipe
from django.utils import timezone
from urllib.parse import urlencode

from django.contrib import messages
from django.core.management import call_command
from django.db import transaction
from django.db.models import Case, IntegerField, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from inventory.models import Ingredient
from .models import DietMenu, DietPlan, Menu, Recipe
from forecasting.models import AttendancePrediction


CATEGORY_ORDER = ["밥", "국", "주반찬", "부반찬", "김치", "간식"]

SORT_ORDER = Case(
    *[When(menu__category=cat, then=Value(pos)) for pos, cat in enumerate(CATEGORY_ORDER)],
    default=Value(len(CATEGORY_ORDER)),
    output_field=IntegerField(),
)


def to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def meal_home(request):
    return render(request, "meals/meal_home.html")


def mealplan_create(request):
    menus = Menu.objects.all().order_by("name")
    selected_date = request.GET.get("date") or request.POST.get("meal_date")

    existing_meals = {
        "breakfast": [],
        "lunch": [],
        "dinner": [],
    }

    if selected_date:
        plans = (
            DietPlan.objects.filter(target_date=selected_date)
            .prefetch_related("diet_menus__menu")
            .order_by("meal_type")
        )

        for plan in plans:
            menu_ids = [item.menu_id for item in plan.diet_menus.all()]

            if plan.meal_type == "조식":
                existing_meals["breakfast"] = menu_ids
            elif plan.meal_type == "중식":
                existing_meals["lunch"] = menu_ids
            elif plan.meal_type == "석식":
                existing_meals["dinner"] = menu_ids

    if request.method == "POST":
        meal_date = request.POST.get("meal_date")
        breakfast_menu_ids = request.POST.getlist("breakfast_menu")
        lunch_menu_ids = request.POST.getlist("lunch_menu")
        dinner_menu_ids = request.POST.getlist("dinner_menu")

        if not meal_date:
            messages.error(request, "날짜를 선택해주세요.")
            return redirect("meals:mealplan_create")

        DietPlan.objects.filter(target_date=meal_date).delete()

        created_count = 0
        meal_type_map = {
            "조식": breakfast_menu_ids,
            "중식": lunch_menu_ids,
            "석식": dinner_menu_ids,
        }

        for meal_type, menu_ids in meal_type_map.items():
            valid_menu_ids = [menu_id for menu_id in menu_ids if menu_id]

            if valid_menu_ids:
                diet_plan = DietPlan.objects.create(
                    target_date=meal_date,
                    meal_type=meal_type,
                )

                for menu_id in valid_menu_ids:
                    DietMenu.objects.create(
                        diet_plan=diet_plan,
                        menu_id=menu_id,
                    )

                created_count += 1

        if created_count == 0:
            messages.warning(request, "선택된 메뉴가 없어 빈 식단으로 저장되지 않았습니다.")
        else:
            messages.success(request, f"{meal_date} 식단이 저장되었습니다.")

        return redirect(f"{reverse('meals:mealplan_create')}?date={meal_date}")

    context = {
        "menus": menus,
        "selected_date": selected_date,
        "existing_meals": existing_meals,
    }

    return render(request, "meals/mealplan_create.html", context)


def mealplan_list(request):
    today = date.today()
    selected_year = int(request.GET.get("year", today.year))
    selected_month = int(request.GET.get("month", today.month))

    plans = (
        DietPlan.objects.filter(
            target_date__year=selected_year,
            target_date__month=selected_month,
        )
        .prefetch_related("diet_menus__menu")
        .order_by("target_date", "meal_type")
    )

    meal_map = {}

    for plan in plans:
        day = plan.target_date.day
        meal_map.setdefault(
            day,
            {
                "breakfast": [],
                "lunch": [],
                "dinner": [],
                "breakfast_dicts": [],
                "lunch_dicts": [],
                "dinner_dicts": [],
            },
        )

        sorted_diet_menus = plan.diet_menus.all().select_related("menu").order_by(SORT_ORDER)
        menu_names = [item.menu.name for item in sorted_diet_menus]
        menu_dicts = [{"id": item.menu.id, "name": item.menu.name} for item in sorted_diet_menus]

        if plan.meal_type == "조식":
            meal_map[day]["breakfast"] = menu_names
            meal_map[day]["breakfast_dicts"] = json.dumps(menu_dicts)
        elif plan.meal_type == "중식":
            meal_map[day]["lunch"] = menu_names
            meal_map[day]["lunch_dicts"] = json.dumps(menu_dicts)
        elif plan.meal_type == "석식":
            meal_map[day]["dinner"] = menu_names
            meal_map[day]["dinner_dicts"] = json.dumps(menu_dicts)

    calendar_weeks = []
    month_calendar = calendar.Calendar(firstweekday=calendar.SUNDAY)

    for week in month_calendar.monthdayscalendar(selected_year, selected_month):
        week_cells = []

        for day_num in week:
            if day_num == 0:
                week_cells.append(None)
                continue

            week_cells.append(
                {
                    "day": day_num,
                    "date": date(selected_year, selected_month, day_num),
                    "is_today": (
                        today.year == selected_year
                        and today.month == selected_month
                        and today.day == day_num
                    ),
                    "meals": meal_map.get(
                        day_num,
                        {
                            "breakfast": [],
                            "lunch": [],
                            "dinner": [],
                            "breakfast_dicts": [],
                            "lunch_dicts": [],
                            "dinner_dicts": [],
                        },
                    ),
                }
            )

        calendar_weeks.append(week_cells)

    context = {
        "selected_year": selected_year,
        "selected_month": selected_month,
        "months": range(1, 13),
        "calendar_weeks": calendar_weeks,
        "today_year": today.year,
        "today_month": today.month,
    }

    return render(request, "meals/mealplan_list.html", context)


def save_recipe_rows(menu, ingredient_ids, amounts):
    valid_count = 0
    skipped_count = 0
    seen_ingredient_ids = set()

    for ingredient_id, amount in zip(ingredient_ids, amounts):
        if not ingredient_id or not amount:
            continue

        amount_decimal = to_decimal(amount)

        if amount_decimal is None or amount_decimal <= 0:
            skipped_count += 1
            continue

        try:
            ingredient = Ingredient.objects.get(id=ingredient_id)
        except Ingredient.DoesNotExist:
            skipped_count += 1
            continue

        if ingredient.id in seen_ingredient_ids:
            skipped_count += 1
            continue

        seen_ingredient_ids.add(ingredient.id)

        Recipe.objects.update_or_create(
            menu=menu,
            ingredient=ingredient,
            defaults={"required_amount": amount_decimal},
        )

        valid_count += 1

    return valid_count, skipped_count


def recipe_create(request):
    menus = Menu.objects.all().order_by("name")
    ingredients = Ingredient.objects.all().order_by("name")

    if request.method == "POST":
        menu_id = request.POST.get("menu_id")
        ingredient_ids = request.POST.getlist("ingredient_id[]")
        required_amounts = request.POST.getlist("required_amount[]")

        if not menu_id:
            messages.error(request, "수정할 메뉴를 선택해주세요.")
            return redirect("meals:recipe_create")

        menu = get_object_or_404(Menu, id=menu_id)

        with transaction.atomic():
            Recipe.objects.filter(menu=menu).delete()
            valid_count, skipped_count = save_recipe_rows(menu, ingredient_ids, required_amounts)

        if valid_count:
            messages.success(request, f"{menu.name} 레시피 식재료 {valid_count}개가 저장되었습니다.")
        else:
            messages.warning(request, "저장된 식재료가 없습니다. 식재료 검색 후 후보를 클릭했는지 확인해주세요.")

        if skipped_count:
            messages.warning(request, f"중복/오류 입력 {skipped_count}건은 제외했습니다.")

        return redirect("meals:menu_list")

    context = {
        "menus": menus,
        "ingredients": ingredients,
    }

    return render(request, "meals/recipe_create.html", context)


def menu_create(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        category = request.POST.get("category")
        ingredient_ids = request.POST.getlist("ingredient_id[]")
        amounts = request.POST.getlist("ing_amount[]")

        if not name or not category:
            messages.error(request, "메뉴명과 카테고리를 입력해주세요.")
            return render(request, "meals/menu_create.html")

        with transaction.atomic():
            menu = Menu.objects.create(
                name=name,
                category=category,
            )
            valid_count, skipped_count = save_recipe_rows(menu, ingredient_ids, amounts)

        if valid_count:
            messages.success(request, f"{menu.name} 메뉴와 식재료 {valid_count}개가 저장되었습니다.")
        else:
            messages.warning(request, f"{menu.name} 메뉴는 저장되었지만 연결된 식재료가 없습니다. 식재료 검색 후 후보를 클릭했는지 확인해주세요.")

        if skipped_count:
            messages.warning(request, f"중복/오류 입력 {skipped_count}건은 제외했습니다.")

        return redirect("meals:menu_list")

    return render(request, "meals/menu_create.html")


def menu_list(request):
    q = request.GET.get("q", "")
    category = request.GET.get("category", "")

    menus = Menu.objects.all().prefetch_related("recipes__ingredient")

    if q:
        menus = menus.filter(name__icontains=q)

    if category:
        menus = menus.filter(category=category)

    return render(request, "meals/menu_list.html", {"menus": menus})


def menu_delete(request, menu_id):
    menu = get_object_or_404(Menu, id=menu_id)
    menu.delete()
    messages.success(request, "메뉴가 삭제되었습니다.")
    return redirect("meals:menu_list")


def menu_update(request, menu_id):
    menu = get_object_or_404(Menu.objects.prefetch_related("recipes__ingredient"), id=menu_id)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        category = request.POST.get("category")
        ingredient_ids = request.POST.getlist("ingredient_id[]")
        amounts = request.POST.getlist("ing_amount[]")

        if not name or not category:
            messages.error(request, "메뉴명과 카테고리를 입력해주세요.")
            return render(request, "meals/menu_update.html", {"menu": menu})

        with transaction.atomic():
            menu.name = name
            menu.category = category
            menu.save()

            Recipe.objects.filter(menu=menu).delete()
            valid_count, skipped_count = save_recipe_rows(menu, ingredient_ids, amounts)

        if valid_count:
            messages.success(request, f"{menu.name} 레시피 식재료 {valid_count}개가 저장되었습니다.")
        else:
            messages.warning(request, f"{menu.name} 메뉴는 저장되었지만 연결된 식재료가 없습니다. 식재료 검색 후 후보를 클릭했는지 확인해주세요.")

        if skipped_count:
            messages.warning(request, f"중복/오류 입력 {skipped_count}건은 제외했습니다.")

        return redirect("meals:menu_list")

    return render(request, "meals/menu_update.html", {"menu": menu})


def deduct_inventory_view(request):
    if request.method == "POST":
        date_str = request.POST.get("target_date")
        if not date_str:
            date_str = timezone.now().date().strftime('%Y-%m-%d')

        ingredients_summary = {}

        try:
            # 1. 당일 식단표 긁어오기
            day_plans = DietPlan.objects.filter(target_date=date_str)
            
            print(f"\n" + "="*50)
            print(f"[🤖 하이브리드 AI 식수 추적 가동] 날짜: {date_str}")

            for plan in day_plans:
                headcount = 100  # 기본 방어선 값
                
                # 🔄 끼니 매칭용 딕셔너리 (DietPlan 한글 ➡️ AttendancePrediction 영문 변환)
                # 만약 AttendancePrediction도 한글('중식')로 저장된다면 아래 매핑 없이 바로 쓰시면 됩니다.
                meal_mapping = {
                    '조식': 'breakfast',
                    '중식': 'lunch',
                    '석식': 'dinner'
                }
                target_meal_type = meal_mapping.get(plan.meal_type, 'lunch')

                # 🎯 [루트 1] 원래 설계한 1:1 MealForecast 테이블 먼저 찔러보기
                if hasattr(plan, 'forecast') and plan.forecast:
                    headcount = plan.forecast.predicted_count
                    print(f"  ⭕ [루트1 성공] DietPlan ID {plan.id}와 1:1 매핑된 예측치 반영: {headcount}명")
                
                # 🎯 [루트 2] 1:1이 비어있다면? 날짜와 끼니 조건으로 AttendancePrediction 대장 직접 타겟팅!
                else:
                    pred_record = AttendancePrediction.objects.filter(
                        prediction_date=date_str,
                        meal_type=target_meal_type  # 또는 plan.meal_type (디비 스펙에 맞춤)
                    ).first()

                    if pred_record:
                        headcount = pred_record.predicted_count
                        print(f"  ⚡ [루트2 성공] 날짜/끼니({date_str} {plan.meal_type}) 직접 조인 성공 -> AI 예측치: {headcount}명 반영")
                    else:
                        # 3순위 방어선: 둘 다 없으면 디비 기본값이나 100명 대입
                        headcount = plan.headcount if plan.headcount > 0 else 100
                        print(f"  ⚠️ [루트3 방어] AI 예측 대장에도 데이터가 없어 기본 식수 {headcount}명 적용")

                # 2. 메뉴 및 레시피 순회 연산
                diet_menus = plan.diet_menus.all()
                for dm in diet_menus:
                    recipes = dm.menu.recipes.all()
                    for recipe in recipes:
                        ing_name = recipe.ingredient.name
                        raw_amount = recipe.required_amount
                        required_amount = float(raw_amount) if raw_amount else 0.0
                        
                        # 진짜 찾아낸 AI 예측 headcount 곱하기
                        row_total = required_amount * headcount
                        
                        if ing_name in ingredients_summary:
                            ingredients_summary[ing_name] += row_total
                        else:
                            ingredients_summary[ing_name] = row_total

            print(f"\n[📊 AI 연동 최종 자재 명세서]: {ingredients_summary}")
            print("="*50 + "\n")

        except Exception as e:
            print(f"🚨 [하이브리드 엔진 에러]: {str(e)}")
            messages.error(request, f"데이터 계산 중 오류 발생: {str(e)}")
            return redirect("meals:mealplan_list")

        if not ingredients_summary:
            messages.warning(request, f"{date_str} 날짜에 매칭된 레시피 데이터가 없습니다.")
            return redirect("meals:mealplan_list")

        # 3. 완벽하게 계산된 바구니 세션 적재 후 출고창 토스
        request.session['bulk_ingredients'] = ingredients_summary
        request.session['bulk_date'] = date_str
        
        first_ing_name = list(ingredients_summary.keys())[0]
        first_quantity = ingredients_summary[first_ing_name]
        
        query_params = urlencode({
            'ingredient_name': first_ing_name,
            'quantity': format(first_quantity, '.2f'),
            'is_bulk': 'true'
        })
        
        response = redirect('inventory:inventory_log_create')
        response['Location'] += f'?{query_params}'
        return response

    return redirect("meals:mealplan_list")

def search_menus_api(request):
    query = request.GET.get("q", "").strip()
    menus = list(Menu.objects.all())

    if not menus:
        return JsonResponse({"results": []})

    if not query:
        results = [{"id": m.id, "name": m.name, "category": m.category or ""} for m in menus[:50]]
        return JsonResponse({"results": results})

    documents = [m.name for m in menus]
    documents.append(query)

    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 3))

    try:
        tfidf_matrix = vectorizer.fit_transform(documents)
    except ValueError:
        return JsonResponse({"results": []})

    cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    top_indices = cosine_sim.argsort()[-20:][::-1]

    results = []

    for idx in top_indices:
        if cosine_sim[idx] > 0.0:
            menu = menus[idx]
            results.append(
                {
                    "id": menu.id,
                    "name": menu.name,
                    "category": menu.category or "",
                    "score": float(cosine_sim[idx]),
                }
            )

    return JsonResponse({"results": results})


@csrf_exempt
def add_diet_menu_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            date_str = data.get("date")
            meal_type = data.get("meal_type")
            menu_id = data.get("menu_id")
            menu_name = data.get("menu_name")

            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            if menu_id:
                menu = Menu.objects.get(id=menu_id)
            elif menu_name:
                menu, _ = Menu.objects.get_or_create(
                    name=menu_name,
                    defaults={"category": "기타"},
                )
            else:
                return JsonResponse({"status": "error", "message": "No menu info provided"}, status=400)

            plan, _ = DietPlan.objects.get_or_create(
                target_date=target_date,
                meal_type=meal_type,
            )

            DietMenu.objects.get_or_create(diet_plan=plan, menu=menu)

            sorted_menus = plan.diet_menus.all().select_related("menu").order_by(SORT_ORDER)
            menu_data = [{"id": dm.menu.id, "name": dm.menu.name} for dm in sorted_menus]

            return JsonResponse(
                {
                    "status": "success",
                    "menu_id": menu.id,
                    "menu_name": menu.name,
                    "menus": menu_data,
                }
            )
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error"}, status=405)


@csrf_exempt
def remove_diet_menu_api(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            date_str = data.get("date")
            meal_type = data.get("meal_type")
            menu_id = data.get("menu_id")

            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            plan = DietPlan.objects.get(target_date=target_date, meal_type=meal_type)
            DietMenu.objects.filter(diet_plan=plan, menu_id=menu_id).delete()

            if not plan.diet_menus.exists():
                plan.delete()
                return JsonResponse({"status": "success", "menus": []})

            sorted_menus = plan.diet_menus.all().select_related("menu").order_by(SORT_ORDER)
            menu_data = [{"id": dm.menu.id, "name": dm.menu.name} for dm in sorted_menus]

            return JsonResponse({"status": "success", "menus": menu_data})
        except DietPlan.DoesNotExist:
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

    return JsonResponse({"status": "error"}, status=405)


def weekly_mealplan_create(request):
    start_date_str = request.GET.get("start_date")

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = date.today()
    else:
        start_date = date.today()

    start_date = start_date - timedelta(days=start_date.weekday())

    if request.method == "POST":
        post_start_date_str = request.POST.get("start_date") or start_date.strftime("%Y-%m-%d")
        messages.success(request, "완료되었습니다.")
        return redirect(f"{reverse('meals:weekly_mealplan_create')}?start_date={post_start_date_str}")

    dates = [start_date + timedelta(days=i) for i in range(7)]

    all_plans = (
        DietPlan.objects.filter(
            target_date__gte=dates[0],
            target_date__lte=dates[-1],
        )
        .prefetch_related("diet_menus__menu")
    )

    weekly_data = {}

    for d in dates:
        weekly_data[d] = {
            "조식": [],
            "중식": [],
            "석식": [],
        }

    for plan_obj in all_plans:
        if plan_obj.target_date in weekly_data:
            sorted_diet_menus = plan_obj.diet_menus.all().select_related("menu").order_by(SORT_ORDER)
            menus = [dm.menu for dm in sorted_diet_menus]
            weekly_data[plan_obj.target_date][plan_obj.meal_type] = menus

    days_context = []
    weekdays_list = ["월", "화", "수", "목", "금", "토", "일"]

    for i, d in enumerate(dates):
        days_context.append(
            {
                "date": d,
                "date_str": d.strftime("%Y-%m-%d"),
                "weekday": weekdays_list[i],
                "breakfast": weekly_data[d].get("조식", []),
                "lunch": weekly_data[d].get("중식", []),
                "dinner": weekly_data[d].get("석식", []),
                "is_next_monday": False,
            }
        )

    context = {
        "start_date": start_date,
        "start_date_str": start_date.strftime("%Y-%m-%d"),
        "prev_week": (start_date - timedelta(days=7)).strftime("%Y-%m-%d"),
        "next_week": (start_date + timedelta(days=7)).strftime("%Y-%m-%d"),
        "days_context": days_context,
    }

    return render(request, "meals/weekly_mealplan_create.html", context)

def mealplan_bulk_upload(request):
    if request.method == 'POST':
        file_type = request.POST.get('file_type')
        uploaded_file = request.FILES.get('mealplan_file')

        if not uploaded_file:
            messages.error(request, "업로드된 파일이 없습니다.")
            return render(request, 'meals/mealplan_bulk_upload.html')

        try:
            # 1. 파일 타입별 Pandas 로드
            if file_type == 'xlsx' or uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            elif file_type == 'csv' or uploaded_file.name.endswith('.csv'):
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(uploaded_file, encoding='cp949')
            else:
                messages.error(request, "지원하지 않는 파일 형식입니다.")
                return render(request, 'meals/mealplan_bulk_upload.html')

            # 엑셀 헤더 기둥 검증
            required_columns = ['date', 'meal_type', 'menu_name', 'category']
            if not all(col in df.columns for col in required_columns):
                messages.error(request, "엑셀 양식이 올바르지 않습니다. 헤더(date, meal_type, menu_name, category)를 확인하세요.")
                return render(request, 'meals/mealplan_bulk_upload.html')

            # 2. 🔥 MySQL 트랜잭션 시작 (DietPlan -> Menu -> DietMenu 순차 적재)
            with transaction.atomic():
                success_count = 0
                new_menu_count = 0  # ✨ 신규 생성된 메뉴 개수를 추적할 카운터 변수 추가
                all_menus = list(Menu.objects.all()) # 캐싱으로 매 루프 쿼리 최소화
                
                for index, row in df.iterrows():
                    if pd.isna(row['date']) or pd.isna(row['menu_name']):
                        continue
                        
                    date_val = str(row['date']).strip()
                    meal_type_raw = str(row['meal_type']).strip()
                    menu_name_val = str(row['menu_name']).strip()
                    category_val = str(row['category']).strip() if not pd.isna(row['category']) else '기타'

                    # 💡 [끼니 매핑 튜닝] 엑셀의 '아침/점심/저녁'을 모델의 TextChoices 규칙으로 치환
                    if '아침' in meal_type_raw or '조식' in meal_type_raw:
                        meal_type_val = DietPlan.MealType.BREAKFAST
                    elif '점심' in meal_type_raw or '중식' in meal_type_raw:
                        meal_type_val = DietPlan.MealType.LUNCH
                    elif '저녁' in meal_type_raw or '석식' in meal_type_raw:
                        meal_type_val = DietPlan.MealType.DINNER
                    else:
                        meal_type_val = DietPlan.MealType.OTHER

                    # 💡 [식단 마스터 레코드] DietPlan 생성 또는 기존 객체 가져오기
                    diet_plan, plan_created = DietPlan.objects.get_or_create(
                        target_date=date_val,
                        meal_type=meal_type_val,
                        defaults={'headcount': 0, 'is_served': False}
                    )

                    # 💡 [메뉴 마스터 레코드] 기존에 등록된 메뉴인지 띄어쓰기 무시하고 체크
                    clean_menu_name = menu_name_val.replace(" ", "")
                    matched_menu = None
                    for m in all_menus:
                        if m.name.replace(" ", "") == clean_menu_name:
                            matched_menu = m
                            break
                    
                    # MySQL에 없는 완전 신규 메뉴라면 자동 등록
                    if not matched_menu:
                        matched_menu = Menu.objects.create(
                            name=menu_name_val,
                            category=category_val
                        )
                        all_menus.append(matched_menu) # 다음 루프를 위해 캐시에 추가
                        new_menu_count += 1  # ✨ 새로운 메뉴가 생겼으므로 카운트 증가

                    # 💡 [N:M 매핑 레코드] DietMenu(식단 상세)에 꽂아 넣기
                    DietMenu.objects.get_or_create(
                        diet_plan=diet_plan,
                        menu=matched_menu
                    )
                    
                    success_count += 1

            # 🎯 3. [동적 알림 피드백 시스템] 신규 생성 메뉴 여부에 따른 경고 가이드 출력
            if new_menu_count > 0:
                messages.warning(
                    request, 
                    f"식단 데이터 총 {success_count}건이 일괄 등록되었습니다. "
                    f"이 중 시스템에 등록되어 있지 않던 [신규 메뉴 {new_menu_count}개]가 자동 생성되었습니다. "
                    f"원활한 재고 차감을 위해 '레시피 등록 및 관리' 페이지에서 식재료 내역을 추가해 주세요."
                )
            else:
                messages.success(request, f"MySQL에 총 {success_count}개의 식단 상세 데이터가 완벽하게 일괄 적재되었습니다.")
                
            return redirect('meals:mealplan_list')

        except Exception as e:
            print(f"[MySQL Bulk Error] {e}")
            messages.error(request, f"데이터베이스 적재 실패: {str(e)}")
            return render(request, 'meals/mealplan_bulk_upload.html')

    return render(request, 'meals/mealplan_bulk_upload.html')

def menu_bulk_upload(request):
    if request.method == 'POST':
        file_type = request.POST.get('file_type')
        uploaded_file = request.FILES.get('recipe_file')

        if not uploaded_file:
            messages.error(request, "업로드된 파일이 없습니다.")
            return render(request, 'meals/menu_bulk_upload.html')

        try:
            # 1. 파일 타입별 Pandas 로드
            if file_type == 'xlsx' or uploaded_file.name.endswith('.xlsx'):
                df = pd.read_excel(uploaded_file)
            elif file_type == 'csv' or uploaded_file.name.endswith('.csv'):
                try:
                    df = pd.read_csv(uploaded_file, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(uploaded_file, encoding='cp949')
            else:
                messages.error(request, "지원하지 않는 파일 형식입니다.")
                return render(request, 'meals/menu_bulk_upload.html')

            # 엑셀 헤더 기둥 검증
            required_columns = ['menu_name', 'category', 'ingredient_name', 'required_amount']
            if not all(col in df.columns for col in required_columns):
                messages.error(request, "엑셀 양식이 올바르지 않습니다. 헤더(menu_name, category, ingredient_name, required_amount)를 확인하세요.")
                return render(request, 'meals/menu_bulk_upload.html')

            # 2. 🔥 MySQL 트랜잭션 시작
            with transaction.atomic():
                recipe_success_count = 0
                menu_new_count = 0
                
                all_menus = list(Menu.objects.all())
                all_ingredients = list(Ingredient.objects.all())

                for index, row in df.iterrows():
                    if pd.isna(row['menu_name']) or pd.isna(row['ingredient_name']) or pd.isna(row['required_amount']):
                        continue
                        
                    menu_name_val = str(row['menu_name']).strip()
                    category_val = str(row['category']).strip() if not pd.isna(row['category']) else '기타'
                    ing_name_val = str(row['ingredient_name']).strip()
                    
                    try:
                        amount_val = float(row['required_amount'])
                    except (ValueError, TypeError):
                        # 숫자가 아닌 잘못된 값이 들어왔을 때도 에러 처리 후 롤백
                        raise ValueError(f"{index + 2}번째 행의 사용량({row['required_amount']})이 올바른 숫자가 아닙니다.")

                    # [A 단계] Menu 마스터 검증 및 생성
                    clean_menu_name = menu_name_val.replace(" ", "")
                    matched_menu = None
                    for m in all_menus:
                        if m.name.replace(" ", "") == clean_menu_name:
                            matched_menu = m
                            break
                    
                    if not matched_menu:
                        matched_menu = Menu.objects.create(name=menu_name_val, category=category_val)
                        all_menus.append(matched_menu)
                        menu_new_count += 1

                    # [B 단계] Ingredient 마스터 검증
                    clean_ing_name = ing_name_val.replace(" ", "")
                    matched_ingredient = None
                    for ing in all_ingredients:
                        if ing.name.replace(" ", "") == clean_ing_name:
                            matched_ingredient = ing
                            break

                    # 🚨 [수정 포인트] 자재 대장에 없는 식재료 발견 시 예외를 의도적으로 발생시켜 트랜잭션 전체 취소(Rollback)
                    if not matched_ingredient:
                        raise NameError(
                            f"자재 대장에 존재하지 않는 식재료가 발견되었습니다: [{ing_name_val}] "
                            f"(엑셀 {index + 2}번째 행 확인 요망). "
                            f"재고 관리 탭에서 해당 식재료를 먼저 등록한 뒤 다시 업로드해 주세요."
                        )

                    # [C 단계] Recipe 매핑 적재
                    Recipe.objects.update_or_create(
                        menu=matched_menu,
                        ingredient=matched_ingredient,
                        defaults={'required_amount': amount_val}
                    )
                    recipe_success_count += 1

            # 3. 🎯 한 건의 누락도 없이 100% 완벽하게 성공했을 때만 이리로 넘어옵니다.
            messages.success(
                request, 
                f"총 {recipe_success_count}개의 메뉴 레시피 데이터가 성공적으로 적재되었습니다! "
                f"(새로 추가된 메뉴: {menu_new_count}개)"
            )
            return redirect('meals:menu_list')

        # 🎯 위에서 일부러 터트린 예외(NameError, ValueError)를 가로채서 명확하게 브라우저 화면에 에러를 띄웁니다.
        except (NameError, ValueError) as custom_error:
            print(f"[Recipe Bulk User Error] {custom_error}")
            messages.error(request, str(custom_error))
            return render(request, 'meals/menu_bulk_upload.html')

        except Exception as e:
            print(f"[MySQL Menu Bulk System Error] {e}")
            messages.error(request, f"시스템 오류가 발생했습니다: {str(e)}")
            return render(request, 'meals/menu_bulk_upload.html')

    return render(request, 'meals/menu_bulk_upload.html')