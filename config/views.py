from django.shortcuts import render
from inventory.models import Ingredient  # DB에서 식재료 모델 가져오기

def home(request):
    # DB에 있는 모든 식재료를 가져옵니다.
    all_ingredients = Ingredient.objects.all()
    # 총 몇 개인지 셉니다.
    total_count = all_ingredients.count()
    
    # 화면(HTML)으로 넘겨줄 보따리(context)를 쌉니다.
    context = {
        'total_count': total_count,
        'ingredients': all_ingredients,
    }
    return render(request, "home.html", context)