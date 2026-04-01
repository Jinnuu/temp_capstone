from urllib import request
import calendar
from datetime import datetime, date
from django.shortcuts import render, redirect, get_object_or_404
from .models import Menu, Recipe, DietPlan, DietMenu
from .forms import MenuForm, MealPlanForm
from inventory.models import Ingredient
from django.urls import reverse

def meal_home(request):
    return render(request, "meals/meal_home.html")

def mealplan_create(request):
    menus = Menu.objects.all().order_by("name")

    if request.method == "POST":
        meal_type_map = {
            "breakfast": "조식",
            "lunch": "중식",
            "dinner": "석식",
        }

        weekly_data = {}

        for key, value in request.POST.items():
            if key in ["csrfmiddlewaretoken", "start_date"]:
                continue
            if not value:
                continue

            parts = key.split("_")
            if len(parts) != 3:
                continue

            date_str, meal_key, menu_kind = parts

            if meal_key not in meal_type_map:
                continue

            weekly_data.setdefault((date_str, meal_key), [])
            weekly_data[(date_str, meal_key)].append(value)

        for (date_str, meal_key), menu_ids in weekly_data.items():
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            meal_type = meal_type_map[meal_key]

            diet_plan, _ = DietPlan.objects.get_or_create(
                target_date=target_date,
                meal_type=meal_type,
            )

            diet_plan.diet_menus.all().delete()
            unique_menu_ids = set(menu_ids)

            for menu_id in unique_menu_ids:
                if menu_id:
                    DietMenu.objects.get_or_create(
                        diet_plan=diet_plan,
                        menu_id=menu_id,
                    )

        start_date = request.POST.get("start_date")
        if start_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            return redirect(
                f"{reverse('meals:mealplan_list')}?year={start.year}&month={start.month}"
            )

        return redirect("meals:mealplan_list")

    return render(request, "meals/mealplan_create.html", {"menus": menus})

def mealplan_list(request):
    today = date.today()

    year_param = (request.GET.get("year") or "").strip()
    month_param = (request.GET.get("month") or "").strip()

    selected_year = today.year
    selected_month = today.month

    if month_param:
        if "-" in month_param:
            # ex) "2026-02"
            try:
                parsed_year, parsed_month = month_param.split("-", 1)
                selected_year = int(parsed_year)
                selected_month = int(parsed_month)
            except ValueError:
                selected_year = today.year
                selected_month = today.month
        else:
            # ex) "2"
            try:
                selected_month = int(month_param)
            except ValueError:
                selected_month = today.month

    if year_param:
        try:
            selected_year = int(year_param)
        except ValueError:
            selected_year = today.year
    if not 1 <= selected_month <= 12:
        selected_month = today.month

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
            },
        )

        menu_names = [item.menu.name for item in plan.diet_menus.all()]

        if plan.meal_type == "조식":
            meal_map[day]["breakfast"] = menu_names
        elif plan.meal_type == "중식":
            meal_map[day]["lunch"] = menu_names
        elif plan.meal_type == "석식":
            meal_map[day]["dinner"] = menu_names

    calendar_weeks = []
    for week in calendar.monthcalendar(selected_year, selected_month):
        week_cells = []

        for day_num in week:
            if day_num == 0:
                week_cells.append(None)
                continue

            week_cells.append(
                {
                    "day": day_num,
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

def recipe_create(request):
    menus = Menu.objects.all().order_by("name")
    ingredients = Ingredient.objects.all().order_by("name")

    if request.method == "POST":
        menu_id = request.POST.get("menu_id")
        ingredient_ids = request.POST.getlist("ingredient_id[]")
        required_amounts = request.POST.getlist("required_amount[]")

        if menu_id:
            menu = get_object_or_404(Menu, id=menu_id)

            valid_rows = []
            for ingredient_id, amount in zip(ingredient_ids, required_amounts):
                if ingredient_id and amount:
                    valid_rows.append((ingredient_id, amount))

            if valid_rows:
                menu.recipes.all().delete()

                for ingredient_id, amount in valid_rows:
                    Recipe.objects.create(
                        menu=menu,
                        ingredient_id=ingredient_id,
                        required_amount=amount,
                    )

            return redirect("meals:menu_list")

    context = {
        "menus": menus,
        "ingredients": ingredients,
    }
    return render(request, "meals/recipe_create.html", context)

def menu_create(request):
    if request.method == "POST":
        name = request.POST.get("name")
        category = request.POST.get("category")

        if name and category:
            menu = Menu.objects.create(
                name=name,
                category=category,
            )

            ing_names = request.POST.getlist("ing_name[]")
            ing_amounts = request.POST.getlist("ing_amount[]")

            for ing_name, ing_amount in zip(ing_names, ing_amounts):
                if ing_name and ing_amount:
                    clean_name = ing_name.strip()

                    ingredient = Ingredient.objects.filter(name=clean_name).first()
                    if not ingredient:
                        ingredient = Ingredient.objects.filter(name__icontains=clean_name).first()

                    if ingredient:
                        Recipe.objects.create(
                            menu=menu,
                            ingredient=ingredient,
                            required_amount=ing_amount,
                        )

            return redirect("meals:menu_list")

    return render(request, "meals/menu_create.html")

def menu_list(request):
    menus = Menu.objects.all().prefetch_related("recipes__ingredient")
    return render(request, "meals/menu_list.html", {"menus": menus})

def menu_delete(request, menu_id):
    menu = get_object_or_404(Menu, id=menu_id) # 삭제할 메뉴 콕 집어오기
    menu.delete() # DB에서 흔적도 없이 날려버리기!
    return redirect('meals:menu_list')
def menu_update(request, menu_id):
    # 1. 수정할 메뉴를 DB에서 콕 집어옵니다.
    menu = get_object_or_404(Menu, id=menu_id)

    if request.method == 'POST':
        # 2. 폼에서 날아온 새로운 이름과 카테고리로 덮어쓰기!
        menu.name = request.POST.get('name')
        menu.category = request.POST.get('category')
        menu.save()

        # 3. 🚀 마법의 꼼수: 기존에 연결되어 있던 레시피를 싹 다 지워버립니다!
        menu.recipes.all().delete()

        # 4. 그리고 화면에서 새로 받아온 식재료들로 다시 레시피를 만듭니다!
        ing_names = request.POST.getlist('ing_name[]')
        ing_amounts = request.POST.getlist('ing_amount[]')

        for name, amount in zip(ing_names, ing_amounts):
            if name and amount:
                clean_name = name.strip()
                
                # 💡 1순위: 이름이 100% 완벽하게 똑같은 식재료를 먼저 찾습니다!
                ingredient = Ingredient.objects.filter(name=clean_name).first()
                
                # 💡 2순위: 완벽히 똑같은 이름이 DB에 없다면, 그때만 '포함된' 단어로 찾습니다!
                if not ingredient:
                    ingredient = Ingredient.objects.filter(name__icontains=clean_name).first()
                    
                if ingredient:
                    Recipe.objects.create(
                        menu=menu,
                        ingredient=ingredient,
                        required_amount=amount
                    )

        # 수정이 끝나면 다시 메뉴판 화면으로!
        return redirect('meals:menu_list')

    # 처음 들어왔을 때 (GET): 기존 메뉴 정보를 html로 넘겨줍니다.
    return render(request, "meals/menu_update.html", {'menu': menu})