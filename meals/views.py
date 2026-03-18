from django.shortcuts import render

from django.shortcuts import render


def meal_home(request):
    return render(request, "meals/meal_home.html")


def menu_create(request):
    return render(request, "meals/menu_create.html")


def menu_list(request):
    return render(request, "meals/menu_list.html")


def recipe_create(request):
    return render(request, "meals/recipe_create.html")


def mealplan_create(request):
    return render(request, "meals/mealplan_create.html")


def mealplan_list(request):
    return render(request, "meals/mealplan_list.html")
