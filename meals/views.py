import calendar
from datetime import datetime, date, timedelta

from django.http import JsonResponse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import json
import openpyxl
from django.views.decorators.csrf import csrf_exempt

from django.contrib import messages
from django.core.management import call_command
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db import transaction

from .models import Menu, Recipe, DietPlan, DietMenu
from inventory.models import Ingredient
from django.db.models import Case, When, Value, IntegerField

CATEGORY_ORDER = ['밥', '국', '주반찬', '부반찬', '김치', '간식']
SORT_ORDER = Case(
    *[When(menu__category=cat, then=Value(pos)) for pos, cat in enumerate(CATEGORY_ORDER)],
    default=Value(len(CATEGORY_ORDER)),
    output_field=IntegerField(),
)


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
                "breakfast_dicts": [],
                "lunch_dicts": [],
                "dinner_dicts": [],
            },
        )

        sorted_diet_menus = plan.diet_menus.all().select_related('menu').order_by(SORT_ORDER)
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
    return redirect("meals:menu_list")


def menu_update(request, menu_id):
    menu = get_object_or_404(Menu, id=menu_id)

    if request.method == "POST":
        menu.name = request.POST.get("name")
        menu.category = request.POST.get("category")
        menu.save()

        # 데이터 안전을 위해 트랜잭션 블록 안에서 레시피 재빌드
        with transaction.atomic():
            # 1. 기존 레시피 일괄 삭제
            menu.recipes.all().delete()

            ing_names = request.POST.getlist("ing_name[]")
            ing_amounts = request.POST.getlist("ing_amount[]")

            # 2. 리스트 돌면서 대조 작업 시작
            for name, amount in zip(ing_names, ing_amounts):
                # 이름과 수량이 실제로 존재할 때만 처리
                if name and amount:
                    clean_name = name.strip()
                    
                    # 💡 [핵심] 띄어쓰기를 완전히 무시하고 DB 뒤지기
                    clean_search_name = clean_name.replace(" ", "")
                    all_ingredients = Ingredient.objects.all()
                    ingredient = None

                    for ing in all_ingredients:
                        if ing.name.replace(" ", "") == clean_search_name:
                            ingredient = ing
                            break

                    # 💡 [보완] 만약 포함 조건이나 공백 제거 조건으로도 없다면 새로 개설해서 매칭
                    if not ingredient:
                        # safe_stock_level NOT NULL 제약조건 방어 코드 포함
                        ingredient = Ingredient.objects.create(
                            name=clean_name,
                            category='기타',
                            unit='kg',
                            safe_stock_level=0
                        )

                    # 3. 안전하게 float 변환 후 레시피 생성
                    try:
                        Recipe.objects.create(
                            menu=menu,
                            ingredient=ingredient,
                            required_amount=float(amount)
                        )
                    except ValueError:
                        print(f"[WARN] 사용량 숫자가 유효하지 않음: {amount}")
                        continue

        messages.success(request, f"'{menu.name}' 메뉴의 레시피 정보가 업데이트되었습니다.")
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
    query = request.GET.get('q', '').strip()
    menus = list(Menu.objects.all())
    
    if not menus:
        return JsonResponse({'results': []})
        
    if not query:
        results = [{"id": m.id, "name": m.name, "category": m.category or ''} for m in menus[:50]]
        return JsonResponse({'results': results})

    documents = [m.name for m in menus]
    documents.append(query)
    
    vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(1, 3)) 
    try:
        tfidf_matrix = vectorizer.fit_transform(documents)
    except ValueError:
        return JsonResponse({'results': []})
        
    cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1]).flatten()
    
    top_indices = cosine_sim.argsort()[-20:][::-1]
    
    results = []
    for idx in top_indices:
        if cosine_sim[idx] > 0.0:
            menu = menus[idx]
            results.append({
                "id": menu.id,
                "name": menu.name,
                "category": menu.category or '',
                "score": float(cosine_sim[idx])
            })
            
    return JsonResponse({'results': results})

@csrf_exempt
def add_diet_menu_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            date_str = data.get('date')
            meal_type = data.get('meal_type')
            menu_id = data.get('menu_id')
            menu_name = data.get('menu_name')
            
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            if menu_id:
                menu = Menu.objects.get(id=menu_id)
            elif menu_name:
                menu, created = Menu.objects.get_or_create(name=menu_name, defaults={'category': '기타'})
            else:
                return JsonResponse({'status': 'error', 'message': 'No menu info provided'}, status=400)
            
            plan, created = DietPlan.objects.get_or_create(
                target_date=target_date, 
                meal_type=meal_type
            )
            
            DietMenu.objects.get_or_create(diet_plan=plan, menu=menu)
            
            # Return sorted menus for this meal
            sorted_menus = plan.diet_menus.all().select_related('menu').order_by(SORT_ORDER)
            menu_data = [{"id": dm.menu.id, "name": dm.menu.name} for dm in sorted_menus]
            
            return JsonResponse({
                'status': 'success', 
                'menu_id': menu.id, 
                'menu_name': menu.name,
                'menus': menu_data
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=405)

@csrf_exempt
def remove_diet_menu_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            date_str = data.get('date')
            meal_type = data.get('meal_type')
            menu_id = data.get('menu_id')
            
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            plan = DietPlan.objects.get(target_date=target_date, meal_type=meal_type)
            DietMenu.objects.filter(diet_plan=plan, menu_id=menu_id).delete()
            
            if not plan.diet_menus.exists():
                plan.delete()
                return JsonResponse({'status': 'success', 'menus': []})
            
            # Return remaining sorted menus
            sorted_menus = plan.diet_menus.all().select_related('menu').order_by(SORT_ORDER)
            menu_data = [{"id": dm.menu.id, "name": dm.menu.name} for dm in sorted_menus]
                
            return JsonResponse({'status': 'success', 'menus': menu_data})
        except DietPlan.DoesNotExist:
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=405)


def weekly_mealplan_create(request):
    start_date_str = request.GET.get("start_date")
    
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = date.today()
    else:
        start_date = date.today()
        
    # start_date를 무조건 해당 주의 월요일로 맞춤
    start_date = start_date - timedelta(days=start_date.weekday())
        
    if request.method == "POST":
        post_start_date_str = request.POST.get("start_date")
        messages.success(request, "완료되었습니다.")
        return redirect(f"{reverse('meals:weekly_mealplan_create')}?start_date={post_start_date_str}")
        
    # GET 렌더링용: 8일치 데이터 가져오기
    dates = [start_date + timedelta(days=i) for i in range(8)]
    
    # 8일치의 DietPlan, DietMenu 조회
    all_plans = DietPlan.objects.filter(
        target_date__gte=dates[0],
        target_date__lte=dates[7]
    ).prefetch_related("diet_menus__menu")
    
    # date -> meal_type -> list of menu objects
    weekly_data = {}
    for d in dates:
        weekly_data[d] = {
            '조식': [],
            '중식': [],
            '석식': []
        }
    
    for plan_obj in all_plans:
        if plan_obj.target_date in weekly_data:
            # 카테고리 순서(밥-국-주-부-김-간)로 정렬
            sorted_diet_menus = plan_obj.diet_menus.all().select_related('menu').order_by(SORT_ORDER)
            menus = [dm.menu for dm in sorted_diet_menus]
            weekly_data[plan_obj.target_date][plan_obj.meal_type] = menus
            
    days_context = []
    weekdays_list = ['월', '화', '수', '목', '금', '토', '일', '월(다음주)']
    
    for i, d in enumerate(dates):
        item = {
            'date': d,
            'date_str': d.strftime('%Y-%m-%d'),
            'weekday': weekdays_list[i],
            'breakfast': weekly_data[d].get('조식', []),
            'lunch': weekly_data[d].get('중식', []),
            'dinner': weekly_data[d].get('석식', []),
            'is_next_monday': (i == 7)
        }
        days_context.append(item)
        
    context = {
        'start_date': start_date,
        'start_date_str': start_date.strftime('%Y-%m-%d'),
        'prev_week': (start_date - timedelta(days=7)).strftime('%Y-%m-%d'),
        'next_week': (start_date + timedelta(days=7)).strftime('%Y-%m-%d'),
        'days_context': days_context,
    }
    
    return render(request, "meals/weekly_mealplan_create.html", context)

def recipe_upload_api(request):
    """
    [진짜 무적 버전]
    엑셀의 행 시작 위치뿐만 아니라, 컬럼(열)의 순서가 뒤바뀌어도 
    헤더 이름('메뉴명', '카테고리', '식재료명', '사용량')을 매칭하여 정확하게 데이터를 파싱합니다.
    """
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        
        try:
            wb = openpyxl.load_workbook(excel_file)
            sheet = wb.active
            
            # 🔍 1. 헤더 위치(행 번호) 및 각 컬럼의 인덱스(열 번호) 찾기
            header_row = None
            col_map = {} # {'메뉴명': 0, '카테고리': 1, ...} 형태로 인덱스 저장
            
            # 상위 20줄을 뒤져서 헤더 행을 찾습니다.
            for r_num in range(1, min(sheet.max_row + 1, 20)):
                row_values = [str(sheet.cell(row=r_num, column=c).value).strip() for c in range(1, sheet.max_column + 1)]
                
                # '메뉴명'과 '식재료명'이 포함된 행을 헤더 행으로 판단
                if "메뉴명" in row_values and "식재료명" in row_values:
                    header_row = r_num
                    # 각 헤더 이름이 몇 번째 인덱스(0부터 시작)에 있는지 기록
                    for idx, val in enumerate(row_values):
                        if "메뉴명" in val: col_map["menu"] = idx
                        elif "카테고리" in val: col_map["category"] = idx
                        elif "식재료명" in val: col_map["ing_name"] = idx
                        elif "사용량" in val: col_map["amount"] = idx
                    break
            
            # 헤더를 못 찾았다면 기본 고정 순서(0, 1, 2, 3)를 안전장치로 설정
            if not header_row:
                header_row = 4  # 기본 헤더 행 위치 가정
                col_map = {"menu": 0, "category": 1, "ing_name": 2, "amount": 3}
                
            start_row = header_row + 1
            success_count = 0
            
            # 🔍 2. 찾아낸 열 인덱스를 기반으로 정확하게 데이터 추출
            for row in sheet.iter_rows(min_row=start_row, values_only=True):
                if not row or row[col_map["menu"]] is None:
                    continue
                
                # 🔥 고정된 row[0] 대신 찾은 위치(col_map)에서 데이터를 쏙쏙 뽑아옵니다!
                menu_name = row[col_map["menu"]]
                category = row[col_map["category"]] if col_map.get("category") < len(row) else "기타"
                ing_name = row[col_map["ing_name"]]
                amount = row[col_map["amount"]] if col_map.get("amount") < len(row) else 0
                
                if not str(menu_name).strip() or not str(ing_name).strip():
                    continue
                
                # [1] 메뉴 가져오거나 생성
                menu, created = Menu.objects.get_or_create(
                    name=str(menu_name).strip(),
                    defaults={'category': category or '기타'}
                )
                
                # [2] 식재료 DB에서 매칭 (공백 무시)
                clean_ing_name = str(ing_name).replace(" ", "")
                all_ingredients = Ingredient.objects.all()
                ingredient = None
                
                for ing in all_ingredients:
                    if ing.name.replace(" ", "") == clean_ing_name:
                        ingredient = ing
                        break
                
                if not ingredient:
                    ingredient = Ingredient.objects.create(
                        name=str(ing_name).strip(), 
                        category='기타', 
                        unit='kg',
                        safe_stock_level=0
                    )
                
                # [3] 레시피 데이터 연결 및 저장
                Recipe.objects.update_or_create(
                    menu=menu,
                    ingredient=ingredient,
                    defaults={'required_amount': float(amount or 0)}
                )
                success_count += 1
                
            messages.success(request, f"엑셀 일괄 업로드 완료! 총 {success_count}건의 레시피 데이터가 안정적으로 반영되었습니다.")
            
        except Exception as e:
            print(f"[ERROR] Excel upload failed: {e}")
            messages.error(request, f"엑셀 파일 파싱 중 오류가 발생했습니다: {e}")
            
    else:
        messages.error(request, f"올바르지 않은 파일 요청입니다.")
        
    return redirect('meals:menu_list')

def search_ingredients_api(request):
    """
    인풋창에 입력한 글자가 포함된 식재료 목록을 JSON으로 반환
    """
    query = request.GET.get('q', '').strip()
    if query:
        # 이름에 검색어가 포함된 식재료 상위 10개 필터링
        ingredients = Ingredient.objects.filter(name__icontains=query)[:10]
        results = [{'id': ing.id, 'name': ing.name} for ing in ingredients]
    else:
        results = []
        
    return JsonResponse({'results': results})

def get_menu_recipes_api(request, menu_id):
    """
    선택된 메뉴의 등록된 레시피(식재료 일람 및 사용량)를 JSON 배열로 변환하여 리턴
    """
    try:
        menu = Menu.objects.get(id=menu_id)
        # 역참조(related_name)인 recipes로 해당 메뉴의 모든 식재료 구성을 조회합니다.
        recipes_queryset = menu.recipes.all()
        
        recipes_list = []
        for r in recipes_queryset:
            recipes_list.append({
                'ingredient_id': r.ingredient.id,
                'ingredient_name': r.ingredient.name,
                'required_amount': float(r.required_amount)
            })
            
        return JsonResponse({
            'status': 'success',
            'recipes': recipes_list
        })
    except Menu.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '존재하지 않는 메뉴입니다.'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)