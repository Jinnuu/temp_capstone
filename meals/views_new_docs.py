"""
신규 실무 문서 뷰 (meals 앱)
- doc_menu_overview: 주간 식단조견표 (A4 세로)
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.shortcuts import render
from .models import DietPlan

WEEKDAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]


def doc_menu_overview(request):
    """[신규] 주간 식단조견표 (실무 양식) - doc_menu_overview.html"""
    start_date_str = request.GET.get("start_date")
    end_date_str = request.GET.get("end_date")
    target_date_str = request.GET.get("date")

    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            target_date = start_date
        except ValueError:
            target_date = date.today()
            start_date = target_date - timedelta(days=target_date.weekday())
            end_date = start_date + timedelta(days=6)
    elif target_date_str or start_date_str:
        raw_date_str = target_date_str or start_date_str
        try:
            target_date = datetime.strptime(raw_date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
        start_date = target_date - timedelta(days=target_date.weekday())
        end_date = start_date + timedelta(days=6)
    else:
        target_date = date.today()
        start_date = target_date - timedelta(days=target_date.weekday())
        end_date = start_date + timedelta(days=6)

    plans = (
        DietPlan.objects.filter(target_date__range=[start_date, end_date])
        .prefetch_related("diet_menus__menu__recipes__ingredient")
        .order_by("target_date", "meal_type")
    )

    diet_plans = []
    total_ingredient_rows = 0

    for plan in plans:
        date_str = f"{plan.target_date.strftime('%m/%d')} ({WEEKDAYS_KO[plan.target_date.weekday()]})"
        headcount = plan.headcount or 500

        menus_data = []
        plan_total_rows = 0

        diet_menus = plan.diet_menus.all().select_related("menu")
        for dm in diet_menus:
            menu = dm.menu
            recipes = menu.recipes.all().select_related("ingredient")

            ing_list = []
            if recipes.exists():
                for recipe in recipes:
                    ing = recipe.ingredient
                    req_amt = recipe.required_amount or Decimal("0")

                    if req_amt < Decimal("10"):
                        portion_g = round(float(req_amt * 1000), 1)
                        if portion_g == int(portion_g):
                            portion_g = int(portion_g)
                        total_qty_val = float(req_amt * headcount)
                    else:
                        portion_g = float(req_amt)
                        if portion_g == int(portion_g):
                            portion_g = int(portion_g)
                        total_qty_val = float(req_amt * headcount / 1000)

                    unit = ing.unit if ing.unit else "kg"
                    total_qty_str = f"{round(total_qty_val, 1)} {unit}"

                    ing_list.append({
                        "name": ing.name,
                        "portion_g": portion_g,
                        "total_qty": total_qty_str,
                        "allergy": ing.description if (ing.description and "알레르기" in ing.description) else "-",
                        "remark": ing.spec or "-",
                    })
            else:
                ing_list.append({
                    "name": "-",
                    "portion_g": "-",
                    "total_qty": "-",
                    "allergy": "-",
                    "remark": "-",
                })

            menus_data.append({
                "name": menu.name,
                "rowspan": len(ing_list),
                "ingredients": ing_list,
            })
            plan_total_rows += len(ing_list)

        diet_plans.append({
            "date_str": date_str,
            "meal_type": plan.meal_type,
            "headcount": headcount,
            "rowspan": plan_total_rows,
            "menus": menus_data,
        })
        total_ingredient_rows += plan_total_rows

    headcount_val = plans.first().headcount if (plans.exists() and plans.first().headcount) else 500

    # Chunk diet_plans into pages for clean pagination and print breaking
    pages = []
    current_page_plans = []
    current_rows = 0

    for plan in diet_plans:
        if current_rows + plan["rowspan"] > 22 and current_page_plans:
            pages.append({
                "page_num": len(pages) + 1,
                "diet_plans": current_page_plans,
            })
            current_page_plans = [plan]
            current_rows = plan["rowspan"]
        else:
            current_page_plans.append(plan)
            current_rows += plan["rowspan"]

    if current_page_plans:
        pages.append({
            "page_num": len(pages) + 1,
            "diet_plans": current_page_plans,
        })

    if not pages:
        pages.append({
            "page_num": 1,
            "diet_plans": [],
        })

    context = {
        "target_date": target_date.strftime("%Y-%m-%d"),
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "monday": start_date.strftime("%Y-%m-%d"),
        "sunday": end_date.strftime("%Y-%m-%d"),
        "headcount": headcount_val,
        "diet_plans": diet_plans,
        "pages": pages,
        "total_pages": len(pages),
        "total_rows": total_ingredient_rows,
    }
    return render(request, "docs/doc_menu_overview.html", context)


