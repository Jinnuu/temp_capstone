from django.shortcuts import render
from django.core.paginator import Paginator
from .models import Ingredient
from django.shortcuts import redirect 
from .forms import InventoryLogForm

def ingredient_list(request):
    # 1. 주소창에서 사용자가 클릭한 '카테고리' 값 가져오기 (없으면 빈칸)
    selected_category = request.GET.get('category', '')
    
    # 2. 일단 모든 데이터를 다 가져옵니다.
    ingredients = Ingredient.objects.all().order_by('id')
    
    # 3. ✨ 만약 카테고리가 선택되었다면? -> 그 카테고리만 필터링(조회)!
    if selected_category:
        ingredients = ingredients.filter(category=selected_category)
        
    # 4. 화면에 '버튼'을 만들기 위해, DB에 있는 고유한 대분류 이름들만 중복 없이 쏙쏙 뽑아옵니다.
    categories = Ingredient.objects.exclude(category__isnull=True).exclude(category__exact='').values_list('category', flat=True).distinct()
    
    # 5. 페이지네이션 (10개씩 자르기)
    paginator = Paginator(ingredients, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # 6. 화면으로 던져줄 보따리 싸기
    context = {
        'page_obj': page_obj,
        'categories': categories,             # 화면에 그릴 카테고리 버튼들 모음
        'selected_category': selected_category, # 현재 어떤 버튼이 눌려있는지 확인하는 용도
    }
    return render(request, 'inventory/ingredient_list.html', context)

def inventory_log_create(request):
    # 1. 사용자가 '저장' 버튼을 눌렀을 때 (POST 요청)
    if request.method == 'POST':
        form = InventoryLogForm(request.POST)
        if form.is_valid():    # 입력한 데이터가 정상이라면?
            form.save()        # DB에 바로 저장!
            # 저장이 끝나면 다시 식재료 목록 화면으로 튕겨 보냅니다.
            return redirect('inventory:ingredient_list') 
            
    # 2. 그냥 처음 주소창을 치고 들어왔을 때 (GET 요청)
    else:
        form = InventoryLogForm() # 빈 입력창을 준비합니다.
        
    return render(request, 'inventory/inventory_log_form.html', {'form': form})