from django.shortcuts import render, redirect, get_object_or_404
from .models import Menu, Recipe # 💡 DB에서 메뉴 데이터를 꺼내오기 위해 모델을 불러옵니다!
from .forms import MenuForm
from inventory.models import Ingredient


def meal_home(request):
    return render(request, "meals/meal_home.html")

def menu_create(request):
    if request.method == 'POST':
        # 1. 폼에서 날아온 메뉴 이름과 카테고리 낚아채기
        menu_name = request.POST.get('name')
        category = request.POST.get('category')

        # 2. 일단 메뉴(Menu) 방부터 하나 만듭니다!
        menu = Menu.objects.create(name=menu_name, category=category)

        # 3. 추가된 여러 개의 식재료 이름과 수량을 리스트 묶음으로 낚아챕니다!
        ing_names = request.POST.getlist('ing_name[]')
        ing_amounts = request.POST.getlist('ing_amount[]')

        # 4. 이름과 수량을 짝지어서 레시피(Recipe)로 저장합니다!
        for name, amount in zip(ing_names, ing_amounts):
            if name and amount: # 빈칸이 아닐 때만 실행
                # 사용자가 적은 글씨(예: "양파")가 DB 식재료 이름에 포함된 녀석을 찾습니다.
                ingredient = Ingredient.objects.filter(name__icontains=name.strip()).first()
                
                # 식재료를 찾았다면? -> 제육볶음 + 양파 레시피 연결!
                if ingredient:
                    Recipe.objects.create(
                        menu=menu,
                        ingredient=ingredient,
                        required_amount=amount
                    )

        # 저장이 모두 끝나면 예쁜 메뉴판 화면으로 튕겨냅니다.
        return redirect('meals:menu_list')

    # 처음 들어왔을 때는 그냥 빈 화면을 보여줍니다.
    return render(request, "meals/menu_create.html")

def menu_list(request):
    # DB에 있는 모든 메뉴와, 그 메뉴에 딸린 레시피(식재료)들을 한 번에 싹 가져옵니다!
    menus = Menu.objects.all().prefetch_related('recipes__ingredient')
    
    
    context = {
        'menus': menus
    }
    return render(request, "meals/menu_list.html", context)

def recipe_create(request):
    return render(request, "meals/recipe_create.html")

def mealplan_create(request):
    return render(request, "meals/mealplan_create.html")

def mealplan_list(request):
    return render(request, "meals/mealplan_list.html")

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