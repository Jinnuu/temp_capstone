import calendar
from datetime import datetime, date

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from .models import Menu, Recipe, DietPlan, DietMenu
from inventory.models import Ingredient


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

        # 기존 식단 삭제 후 다시 생성
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
    menu = get_object_or_404(Menu, id=menu_id)
    menu.delete()
    return redirect("meals:menu_list")


def menu_update(request, menu_id):
    menu = get_object_or_404(Menu, id=menu_id)

    if request.method == "POST":
        menu.name = request.POST.get("name")
        menu.category = request.POST.get("category")
        menu.save()

        menu.recipes.all().delete()

        ing_names = request.POST.getlist("ing_name[]")
        ing_amounts = request.POST.getlist("ing_amount[]")

        for name, amount in zip(ing_names, ing_amounts):
            if name and amount:
                clean_name = name.strip()

                ingredient = Ingredient.objects.filter(name=clean_name).first()

                if not ingredient:
                    ingredient = Ingredient.objects.filter(name__icontains=clean_name).first()

                if ingredient:
                    Recipe.objects.create(
                        menu=menu,
                        ingredient=ingredient,
                        required_amount=amount
                    )

        return redirect("meals:menu_list")

    return render(request, "meals/menu_update.html", {"menu": menu})