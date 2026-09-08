import calendar
import re
import json
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from openpyxl import load_workbook
from django.contrib import messages
from django.core.management import call_command
from django.db import transaction
from django.db.models import Case, IntegerField, Value, When
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from inventory.models import Ingredient
from .models import DietMenu, DietPlan, Menu, Recipe




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
            sorted_diet_menus = plan.diet_menus.all().select_related("menu").order_by("id")
            menu_data = [{"id": dm.menu.id, "name": dm.menu.name} for dm in sorted_diet_menus]

            if plan.meal_type == "조식":
                existing_meals["breakfast"] = menu_data
            elif plan.meal_type == "중식":
                existing_meals["lunch"] = menu_data
            elif plan.meal_type == "석식":
                existing_meals["dinner"] = menu_data

    if request.method == "POST":
        meal_date = request.POST.get("meal_date")
        breakfast_menus = request.POST.getlist("breakfast_menu")
        lunch_menus = request.POST.getlist("lunch_menu")
        dinner_menus = request.POST.getlist("dinner_menu")

        if not meal_date:
            messages.error(request, "날짜를 선택해주세요.")
            return redirect("meals:mealplan_create")

        DietPlan.objects.filter(target_date=meal_date).delete()

        created_count = 0
        meal_type_map = {
            "조식": breakfast_menus,
            "중식": lunch_menus,
            "석식": dinner_menus,
        }

        for meal_type, menu_items in meal_type_map.items():
            valid_items = [m.strip() for m in menu_items if m and m.strip()]

            if valid_items:
                diet_plan = DietPlan.objects.create(
                    target_date=meal_date,
                    meal_type=meal_type,
                )

                for item in valid_items:
                    if item.isdigit():
                        try:
                            menu = Menu.objects.get(id=int(item))
                        except Menu.DoesNotExist:
                            menu, _ = Menu.objects.get_or_create(name=item, defaults={"category": "기타"})
                    else:
                        menu, _ = Menu.objects.get_or_create(name=item, defaults={"category": "기타"})

                    DietMenu.objects.get_or_create(
                        diet_plan=diet_plan,
                        menu=menu,
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

        sorted_diet_menus = plan.diet_menus.all().select_related("menu").order_by("id")
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
        target_date = request.POST.get("target_date")

        if target_date:
            call_command("deduct_daily_inventory", date=target_date)
            messages.success(request, f"{target_date} 기준 식재료 일괄 사용처리가 완료되었습니다.")
        else:
            call_command("deduct_daily_inventory")
            messages.success(request, "오늘 기준 식재료 일괄 사용처리가 완료되었습니다.")

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

            sorted_menus = plan.diet_menus.all().select_related("menu").order_by("id")
            menu_data = [{"id": dm.menu.id, "name": dm.menu.name, "diet_menu_id": dm.id} for dm in sorted_menus]

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

            sorted_menus = plan.diet_menus.all().select_related("menu").order_by("id")
            menu_data = [{"id": dm.menu.id, "name": dm.menu.name, "diet_menu_id": dm.id} for dm in sorted_menus]

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
    next_monday = start_date + timedelta(days=7)

    all_plans = (
        DietPlan.objects.filter(
            target_date__gte=dates[0],
            target_date__lte=next_monday,
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
    weekly_data[next_monday] = {
        "조식": [],
        "중식": [],
        "석식": [],
    }

    for plan_obj in all_plans:
        if plan_obj.target_date in weekly_data:
            # Use model-level sorted method: 밥→국→주반찬→부반찬→과일/간식→음료→기타
            sorted_diet_menus = plan_obj.diet_menus.all().select_related("menu").order_by("id")
            # Pass dict with id (menu_id), diet_menu_id, and name for template use
            weekly_data[plan_obj.target_date][plan_obj.meal_type] = [
                {"id": dm.menu.id, "name": dm.menu.name, "diet_menu_id": dm.id}
                for dm in sorted_diet_menus
            ]

    end_date = dates[-1]
    days_context = []
    weekdays_list = ["월", "화", "수", "목", "금", "토", "일"]

    next_monday_str = next_monday.strftime("%Y-%m-%d")
    next_monday_breakfast = weekly_data[next_monday].get("조식", [])
    next_monday_lunch = weekly_data[next_monday].get("중식", [])

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
                "next_monday_str": next_monday_str if i == 6 else "",
                "next_monday_breakfast": next_monday_breakfast if i == 6 else [],
                "next_monday_lunch": next_monday_lunch if i == 6 else [],
            }
        )

    context = {
        "start_date": start_date,
        "start_date_str": start_date.strftime("%Y-%m-%d"),
        "end_date_str": end_date.strftime("%Y-%m-%d"),
        "prev_week": (start_date - timedelta(days=7)).strftime("%Y-%m-%d"),
        "next_week": (start_date + timedelta(days=7)).strftime("%Y-%m-%d"),
        "days_context": days_context,
    }

    return render(request, "meals/weekly_mealplan_create.html", context)


def weekly_meal_plan_document(request):
    """
    주간 식단표 문서화 기능을 위한 뷰입니다.
    ?date=YYYY-MM-DD 파라미터를 지원하며, 해당 날짜가 속한 주의 월요일을 기준으로 8일치 데이터를 조회합니다.
    """
    # 1. 파라미터 처리 (date 또는 start_date 인식)
    target_date_str = request.GET.get("date") or request.GET.get("start_date")

    # 2. 동적 날짜 계산
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    # 해당 날짜가 속한 주의 월요일(start_date) 계산
    start_date = target_date - timedelta(days=target_date.weekday())
    end_date = start_date + timedelta(days=6)  # 일요일

    # 3. 8일 데이터 바인딩 (월요일부터 다음 주 월요일까지)
    dates = [start_date + timedelta(days=i) for i in range(8)]

    # 8일간의 식단 데이터를 한 번에 가져옴
    all_plans = (
        DietPlan.objects.filter(
            target_date__gte=dates[0],
            target_date__lte=dates[7],
        )
        .prefetch_related("diet_menus__menu")
    )

    # 데이터를 날짜 및 끼니별로 매핑
    weekly_data = {d: {"조식": [], "중식": [], "석식": []} for d in dates}

    for plan_obj in all_plans:
        if plan_obj.target_date in weekly_data:
            # 카테고리 순서(SORT_ORDER)에 따라 메뉴 정렬
            sorted_diet_menus = plan_obj.diet_menus.all().select_related("menu").order_by("id")
            menus = [dm.menu.name for dm in sorted_diet_menus]
            weekly_data[plan_obj.target_date][plan_obj.meal_type] = menus

    # 템플릿에 전달할 7일(월~일) 데이터 구성
    days_context = []
    weekdays_list = ["월", "화", "수", "목", "금", "토", "일"]

    for i in range(7):
        d = dates[i]
        day_info = {
            "date": d,
            "date_str": d.strftime("%Y-%m-%d"),
            "weekday": weekdays_list[i],
            "breakfast": weekly_data[d].get("조식", []),
            "lunch": weekly_data[d].get("중식", []),
            "dinner": weekly_data[d].get("석식", []),
            "remarks": [],
        }

        # 특이사항: 일요일(index 6)의 비고 칸에 다음 주 월요일 조식 데이터 매칭
        if i == 6:
            next_monday = dates[7]
            day_info["remarks"] = weekly_data[next_monday].get("조식", [])

        days_context.append(day_info)

    # 4. 네비게이션 및 상세 컨텍스트 전달
    context = {
        "start_date": start_date,
        "start_date_str": start_date.strftime("%Y-%m-%d"),
        "end_date_str": end_date.strftime("%Y-%m-%d"),
        "prev_week": (start_date - timedelta(days=7)).strftime("%Y-%m-%d"),
        "next_week": (start_date + timedelta(days=7)).strftime("%Y-%m-%d"),
        "days_context": days_context,
    }

    # 확인된 실존 템플릿 경로로 수정
    return render(request, "docs/weekly_report.html", context)


def monthly_meal_plan_document(request):
    """
    월간 식단표 문서화 기능을 위한 뷰입니다. (조회 전용)
    """
    today = date.today()
    selected_year = int(request.GET.get("year", today.year))
    selected_month = int(request.GET.get("month", today.month))

    # 해당 월의 식단 데이터 조회
    plans = (
        DietPlan.objects.filter(
            target_date__year=selected_year,
            target_date__month=selected_month,
        )
        .prefetch_related("diet_menus__menu")
        .order_by("target_date", "meal_type")
    )

    # 데이터 매핑 {day: {breakfast: [], ...}}
    meal_map = {}
    for plan in plans:
        day = plan.target_date.day
        meal_map.setdefault(day, {"breakfast": [], "lunch": [], "dinner": []})

        sorted_diet_menus = plan.diet_menus.all().select_related("menu").order_by("id")
        menu_names = [item.menu.name for item in sorted_diet_menus]

        if plan.meal_type == "조식":
            meal_map[day]["breakfast"] = menu_names
        elif plan.meal_type == "중식":
            meal_map[day]["lunch"] = menu_names
        elif plan.meal_type == "석식":
            meal_map[day]["dinner"] = menu_names

    # 달력 구조 생성 (일~토)
    calendar_weeks = []
    month_calendar = calendar.Calendar(firstweekday=calendar.SUNDAY)

    for week in month_calendar.monthdayscalendar(selected_year, selected_month):
        week_cells = []
        for day_num in week:
            if day_num == 0:
                week_cells.append(None)
            else:
                week_cells.append(
                    {
                        "day": day_num,
                        "meals": meal_map.get(day_num, {"breakfast": [], "lunch": [], "dinner": []}),
                    }
                )
        calendar_weeks.append(week_cells)

    context = {
        "selected_year": selected_year,
        "selected_month": selected_month,
        "years": range(today.year - 1, today.year + 2),
        "months": range(1, 13),
        "calendar_weeks": calendar_weeks,
    }

    return render(request, "docs/monthly_report.html", context)


def export_weekly_mealplan_excel(request):
    """
    주간 식단표(8일치) 데이터를 엑셀 파일로 내보냅니다.
    """
    # 1. 날짜 파라미터 처리
    target_date_str = request.GET.get("date") or request.GET.get("start_date")
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    start_date = target_date - timedelta(days=target_date.weekday())
    dates = [start_date + timedelta(days=i) for i in range(8)]

    # 2. 데이터 조회
    all_plans = (
        DietPlan.objects.filter(
            target_date__gte=dates[0],
            target_date__lte=dates[7],
        )
        .prefetch_related("diet_menus__menu")
    )

    weekly_data = {d: {"조식": [], "중식": [], "석식": []} for d in dates}
    for plan_obj in all_plans:
        if plan_obj.target_date in weekly_data:
            sorted_diet_menus = plan_obj.diet_menus.all().select_related("menu").order_by("id")
            menus = [dm.menu.name for dm in sorted_diet_menus]
            weekly_data[plan_obj.target_date][plan_obj.meal_type] = menus

    # 3. 엑셀 워크북 생성
    wb = Workbook()
    ws = wb.active
    ws.title = f"주간식단표_{start_date.strftime('%m%d')}"

    # 스타일 설정
    header_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    header_font = Font(bold=True)

    # 4. 헤더 작성 (가로축: 월~일)
    weekdays_list = ["월", "화", "수", "목", "금", "토", "일"]
    ws.cell(row=1, column=1, value="구분").font = header_font
    ws.cell(row=1, column=1).fill = header_fill
    ws.cell(row=1, column=1).alignment = center_align
    ws.cell(row=1, column=1).border = border

    for i, (d, w) in enumerate(zip(dates[:7], weekdays_list)):
        cell = ws.cell(row=1, column=i + 2, value=f"{d.strftime('%m/%d')}({w})")
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = border

    # 컬럼 너비 조정
    ws.column_dimensions["A"].width = 12
    for col in "BCDEFGH":
        ws.column_dimensions[col].width = 20

    # 5. 데이터 작성 (세로축: 조식, 중식, 석식, 비고)
    meal_types = ["조식", "중식", "석식", "비고"]
    for r_idx, meal_type in enumerate(meal_types):
        row_num = r_idx + 2
        label_cell = ws.cell(row=row_num, column=1, value=meal_type)
        label_cell.font = header_font
        label_cell.fill = header_fill
        label_cell.alignment = center_align
        label_cell.border = border
        ws.row_dimensions[row_num].height = 60

        for c_idx in range(7):
            d = dates[c_idx]
            col_num = c_idx + 2
            
            if meal_type == "비고":
                if c_idx == 6: # 일요일
                    next_monday = dates[7]
                    val = "[다음주 월요일 조식]\n" + "\n".join(weekly_data[next_monday].get("조식", []))
                    cell = ws.cell(row=row_num, column=col_num, value=val)
                    cell.font = Font(color="0000FF") # 파란색
                else:
                    cell = ws.cell(row=row_num, column=col_num, value="-")
            else:
                menus = weekly_data[d].get(meal_type, [])
                cell = ws.cell(row=row_num, column=col_num, value="\n".join(menus))
            
            cell.alignment = center_align
            cell.border = border

    # 6. HTTP 응답 반환
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    filename = f"Weekly_MealPlan_{start_date.strftime('%Y-%m-%d')}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


@csrf_exempt
def delete_diet_menu_api(request, diet_menu_id):
    """
    AJAX: 개별 DietMenu 레코드를 삭제합니다.
    성공 시 해당 끼니의 (정렬된) 메뉴 목록을 반환합니다.
    """
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "POST만 허용됩니다."}, status=405)

    try:
        dm = get_object_or_404(DietMenu, pk=diet_menu_id)
        plan = dm.diet_plan
        dm.delete()

        if not plan.diet_menus.exists():
            plan.delete()
            return JsonResponse({"status": "success", "menus": []})

        sorted_menus = plan.diet_menus.all().select_related("menu").order_by("id")
        menu_data = [{"id": item.menu.id, "name": item.menu.name, "diet_menu_id": item.id} for item in sorted_menus]
        return JsonResponse({"status": "success", "menus": menu_data})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


def bulk_delete_mealplans(request):
    """
    주간 또는 월간 식단 데이터를 일괄로 삭제합니다.
    - 주간 삭제: POST { start_date, end_date } 또는 GET start_date + end_date
    - 월간 삭제: POST { year, month } 또는 GET year + month
    """
    if request.method not in ("POST", "GET"):
        return JsonResponse({"status": "error"}, status=405)

    params = request.POST if request.method == "POST" else request.GET
    redirect_url = params.get("redirect_url") or reverse("meals:mealplan_list")

    try:
        # 주간 삭제
        start_date_str = params.get("start_date")
        end_date_str = params.get("end_date")
        year_str = params.get("year")
        month_str = params.get("month")

        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            deleted_count, _ = DietPlan.objects.filter(
                target_date__gte=start_date, target_date__lte=end_date
            ).delete()
            messages.success(request, f"{start_date_str}~{end_date_str} 기간의 식단 {deleted_count}건이 삭제되었습니다.")
        elif year_str and month_str:
            year = int(year_str)
            month = int(month_str)
            deleted_count, _ = DietPlan.objects.filter(
                target_date__year=year, target_date__month=month
            ).delete()
            messages.success(request, f"{year}년 {month}월 전체 식단 {deleted_count}건이 삭제되었습니다.")
        else:
            messages.error(request, "삭제할 기간 정보가 올바르지 않습니다.")
    except Exception as e:
        messages.error(request, f"식단 삭제 중 오류가 발생했습니다: {str(e)}")

    return redirect(redirect_url)


def weekly_recipe_report(request):
    """
    주간 레시피(식재료 총량) 문서화 신규 뷰.
    파라미터로 기간(start_date, end_date)과 지정 인원수(headcount)를 받아
    일자 -> 끼니 -> 메뉴 -> 식재료 필요 총량을 계산하여 전달합니다.
    """
    start_date_str = request.GET.get("start_date", "").strip()
    end_date_str = request.GET.get("end_date", "").strip()
    date_str = request.GET.get("date", "").strip()
    headcount_str = request.GET.get("headcount", "100").strip()

    try:
        headcount = int(headcount_str)
        if headcount <= 0:
            headcount = 100
    except (ValueError, TypeError):
        headcount = 100

    today = date.today()
    if date_str and not start_date_str:
        try:
            ref_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            ref_date = today
        start_date = ref_date - timedelta(days=ref_date.weekday())
        end_date = start_date + timedelta(days=6)
    else:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else today - timedelta(days=today.weekday())
        except ValueError:
            start_date = today - timedelta(days=today.weekday())

        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else start_date + timedelta(days=6)
        except ValueError:
            end_date = start_date + timedelta(days=6)

    if end_date < start_date:
        end_date = start_date

    meal_order = Case(
        When(meal_type="조식", then=Value(1)),
        When(meal_type="중식", then=Value(2)),
        When(meal_type="석식", then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )
    category_order = ["밥", "국", "주반찬", "부반찬", "김치", "간식"]
    sort_order = Case(
        *[When(menu__category=cat, then=Value(pos)) for pos, cat in enumerate(category_order)],
        default=Value(len(category_order)),
        output_field=IntegerField(),
    )
    weekdays_ko = ["월", "화", "수", "목", "금", "토", "일"]

    plans = (
        DietPlan.objects.filter(target_date__range=[start_date, end_date])
        .prefetch_related("diet_menus__menu__recipes__ingredient")
        .order_by("target_date", meal_order)
    )

    report_data = []
    for plan in plans:
        dt = plan.target_date
        dt_display = f"{dt.strftime('%m/%d')}({weekdays_ko[dt.weekday()]})"
        meal_display = f"{dt_display} {plan.meal_type}"

        plan_item = {
            "target_date": dt,
            "target_date_display": dt_display,
            "meal_type": plan.meal_type,
            "meal_display": meal_display,
            "menus": [],
            "total_rows": 0,
        }

        sorted_diet_menus = plan.diet_menus.all().select_related("menu").order_by(sort_order)
        plan_total_rows = 0

        for diet_menu in sorted_diet_menus:
            menu = diet_menu.menu
            recipes = list(menu.recipes.all().select_related("ingredient"))
            ing_count = len(recipes) if recipes else 1
            plan_total_rows += ing_count

            menu_item = {
                "name": menu.name,
                "category": menu.category or "-",
                "ingredients": [],
                "row_span": ing_count,
            }

            for recipe in recipes:
                ing = recipe.ingredient
                req_amount = recipe.required_amount or Decimal("0")
                total_needed = req_amount * Decimal(headcount)

                if total_needed % 1 == 0:
                    needed_qty_display = int(total_needed)
                else:
                    needed_qty_display = round(float(total_needed), 2)

                if req_amount % 1 == 0:
                    req_amount_display = int(req_amount)
                else:
                    req_amount_display = float(req_amount)

                menu_item["ingredients"].append(
                    {
                        "name": ing.name,
                        "spec": ing.spec or "-",
                        "unit": ing.unit,
                        "required_amount": req_amount_display,
                        "needed_qty": needed_qty_display,
                    }
                )

            plan_item["menus"].append(menu_item)

        plan_item["total_rows"] = plan_total_rows if plan_total_rows > 0 else 1
        report_data.append(plan_item)

    context = {
        "report_data": report_data,
        "start_date": start_date,
        "end_date": end_date,
        "start_date_str": start_date.strftime("%Y-%m-%d"),
        "end_date_str": end_date.strftime("%Y-%m-%d"),
        "headcount": headcount,
    }
    return render(request, "docs/weekly_recipe_report.html", context)

