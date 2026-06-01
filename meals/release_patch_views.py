from decimal import Decimal, InvalidOperation
import re

import pandas as pd
from django.contrib import messages
from django.db import transaction
from django.db.models import Case, DecimalField, F, Sum, Value, When
from django.shortcuts import redirect, render
from django.utils import timezone

from inventory.models import Ingredient, InventoryLog
from meals.models import DietMenu, DietPlan, Menu, Recipe


MEAL_TYPE_CHOICES = ["조식", "중식", "석식"]


def _norm(value):
    if value is None:
        return ""
    text = str(value).strip().replace("\ufeff", "")
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    return text.lower()


def _decimal(value, default="0"):
    try:
        if value is None or value == "":
            return Decimal(default)
        text = str(value).replace(",", "").strip()
        if not text or text.lower() == "nan":
            return Decimal(default)
        return Decimal(text).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _find_header_row(raw_df, required_any):
    required_norm = [_norm(x) for x in required_any]
    for idx, row in raw_df.iterrows():
        normalized = [_norm(v) for v in row.tolist()]
        if any(key in normalized for key in required_norm):
            return idx
    return None


def _read_recipe_excel(upload_file):
    raw = pd.read_excel(upload_file, header=None, dtype=object)
    header_idx = _find_header_row(raw, ["메뉴명", "식재료명", "재료명", "품목명"])

    if header_idx is None:
        raise ValueError("엑셀 파일에서 '메뉴명' 또는 '식재료명' 헤더를 찾지 못했습니다.")

    headers = [str(v).strip() if v is not None and str(v) != "nan" else "" for v in raw.iloc[header_idx].tolist()]
    df = raw.iloc[header_idx + 1:].copy()
    df.columns = headers
    df = df.dropna(how="all")
    return df


def recipe_upload_page(request):
    """레시피 엑셀 업로드 페이지 + 실제 저장 로직."""
    result_rows = []
    errors = []

    if request.method == "POST":
        upload_file = request.FILES.get("file")

        if not upload_file:
            messages.error(request, "업로드할 엑셀 파일을 선택해주세요.")
            return redirect("meals:recipe_upload_page")

        if not upload_file.name.lower().endswith((".xlsx", ".xls")):
            messages.error(request, "엑셀 파일(.xlsx, .xls)만 업로드할 수 있습니다.")
            return redirect("meals:recipe_upload_page")

        alias = {
            "메뉴명": "menu",
            "메뉴": "menu",
            "카테고리": "category",
            "분류": "category",
            "식재료명": "ingredient",
            "재료명": "ingredient",
            "품목명": "ingredient",
            "사용량": "amount",
            "1인사용량": "amount",
            "1인분사용량": "amount",
            "소요량": "amount",
            "단위": "unit",
        }

        try:
            df = _read_recipe_excel(upload_file)

            positions = {}
            for col in df.columns:
                key = _norm(col)
                for label, field in alias.items():
                    if key == _norm(label) and field not in positions:
                        positions[field] = col

            # 컬럼명이 없지만 앞 5개 컬럼 구조일 때 fallback
            if "menu" not in positions and len(df.columns) >= 5:
                positions = {
                    "menu": df.columns[0],
                    "category": df.columns[1],
                    "ingredient": df.columns[2],
                    "amount": df.columns[3],
                    "unit": df.columns[4],
                }

            required = ["menu", "ingredient", "amount"]
            missing = [field for field in required if field not in positions]
            if missing:
                messages.error(
                    request,
                    "레시피 엑셀에는 메뉴명, 식재료명, 사용량 컬럼이 필요합니다.",
                )
                return redirect("meals:recipe_upload_page")

            created_menu_count = 0
            created_ingredient_count = 0
            saved_recipe_count = 0

            with transaction.atomic():
                for idx, row in df.iterrows():
                    row_no = int(idx) + 2

                    def get_value(field_name):
                        col = positions.get(field_name)
                        if col is None:
                            return None
                        value = row.get(col)
                        if pd.isna(value):
                            return None
                        return value

                    menu_name = str(get_value("menu") or "").strip()
                    category = str(get_value("category") or "기타").strip() or "기타"
                    ingredient_name = str(get_value("ingredient") or "").strip()
                    unit = str(get_value("unit") or "kg").strip() or "kg"
                    amount = _decimal(get_value("amount"), default="0")

                    if not menu_name or menu_name.lower() == "nan":
                        errors.append(f"{row_no}행: 메뉴명이 비어 있습니다.")
                        continue
                    if not ingredient_name or ingredient_name.lower() == "nan":
                        errors.append(f"{row_no}행: 식재료명이 비어 있습니다.")
                        continue
                    if amount <= 0:
                        errors.append(f"{row_no}행: 사용량은 0보다 커야 합니다.")
                        continue

                    menu, menu_created = Menu.objects.get_or_create(
                        name=menu_name,
                        defaults={"category": category},
                    )
                    if menu_created:
                        created_menu_count += 1
                    elif category and menu.category != category:
                        menu.category = category
                        menu.save(update_fields=["category"])

                    ingredient, ingredient_created = Ingredient.objects.get_or_create(
                        name=ingredient_name,
                        defaults={
                            "category": category,
                            "spec": "",
                            "description": "",
                            "unit": unit,
                            "unit_price": 0,
                            "safe_stock_level": 0,
                            "supplier": None,
                            "yearly_demand": 0,
                            "total_amount": 0,
                        },
                    )
                    if ingredient_created:
                        created_ingredient_count += 1
                    else:
                        changed = []
                        if unit and ingredient.unit != unit:
                            ingredient.unit = unit
                            changed.append("unit")
                        if category and not ingredient.category:
                            ingredient.category = category
                            changed.append("category")
                        if changed:
                            ingredient.save(update_fields=changed)

                    Recipe.objects.update_or_create(
                        menu=menu,
                        ingredient=ingredient,
                        defaults={"required_amount": amount},
                    )
                    saved_recipe_count += 1
                    result_rows.append(
                        {
                            "row_no": row_no,
                            "menu": menu.name,
                            "category": menu.category or "",
                            "ingredient": ingredient.name,
                            "amount": amount,
                            "unit": ingredient.unit,
                        }
                    )

            messages.success(
                request,
                f"레시피 업로드 완료: 메뉴 {created_menu_count}개 생성, "
                f"식재료 {created_ingredient_count}개 생성, 레시피 {saved_recipe_count}건 저장.",
            )

        except Exception as exc:
            messages.error(request, f"레시피 업로드 중 오류가 발생했습니다: {exc}")
            return redirect("meals:recipe_upload_page")

    return render(
        request,
        "meals/recipe_upload.html",
        {"result_rows": result_rows, "errors": errors},
    )


def _current_stock(ingredient):
    qs = InventoryLog.objects.filter(ingredient=ingredient)
    in_qty = qs.filter(log_type="입고").aggregate(total=Sum("quantity"))["total"] or Decimal("0")
    adj_qty = qs.filter(log_type="조정").aggregate(total=Sum("quantity"))["total"] or Decimal("0")
    out_qty = qs.filter(log_type="출고").aggregate(total=Sum("quantity"))["total"] or Decimal("0")
    waste_qty = qs.filter(log_type="폐기").aggregate(total=Sum("quantity"))["total"] or Decimal("0")
    return in_qty + adj_qty - out_qty - waste_qty


def _build_deduct_preview(target_date, meal_type=None, override_headcount=None):
    plans = DietPlan.objects.filter(target_date=target_date).prefetch_related(
        "diet_menus__menu__recipes__ingredient"
    )

    if meal_type:
        plans = plans.filter(meal_type=meal_type)

    rows_by_ingredient = {}
    plan_rows = []
    warnings = []

    for plan in plans:
        try:
            plan_headcount = int(override_headcount or plan.headcount or 1)
        except ValueError:
            plan_headcount = int(plan.headcount or 1)

        menus = [dm.menu for dm in plan.diet_menus.select_related("menu")]
        plan_rows.append({"plan": plan, "headcount": plan_headcount, "menus": menus})

        for menu in menus:
            recipes = menu.recipes.select_related("ingredient").all()

            if not recipes:
                warnings.append(f"{plan.meal_type} · {menu.name}: 등록된 레시피가 없습니다.")
                continue

            for recipe in recipes:
                ingredient = recipe.ingredient
                need_qty = (recipe.required_amount or Decimal("0")) * Decimal(plan_headcount)

                if ingredient.id not in rows_by_ingredient:
                    current = _current_stock(ingredient)
                    rows_by_ingredient[ingredient.id] = {
                        "ingredient": ingredient,
                        "current_stock": current,
                        "deduct_qty": Decimal("0"),
                        "after_stock": current,
                        "details": [],
                    }

                row = rows_by_ingredient[ingredient.id]
                row["deduct_qty"] += need_qty
                row["after_stock"] = row["current_stock"] - row["deduct_qty"]
                row["details"].append(
                    {
                        "meal_type": plan.meal_type,
                        "menu": menu.name,
                        "per_person": recipe.required_amount,
                        "headcount": plan_headcount,
                        "need_qty": need_qty,
                    }
                )

    rows = sorted(rows_by_ingredient.values(), key=lambda item: item["ingredient"].name)
    return rows, plan_rows, warnings


def deduct_inventory_view(request):
    """식사 완료 후 재고 차감 preview-confirm view."""
    target_date = (
        request.GET.get("date")
        or request.GET.get("target_date")
        or request.POST.get("target_date")
        or timezone.localdate().isoformat()
    )
    meal_type = request.GET.get("meal_type") or request.POST.get("meal_type") or ""
    override_headcount = request.GET.get("headcount") or request.POST.get("headcount") or None

    rows, plan_rows, warnings = _build_deduct_preview(
        target_date=target_date,
        meal_type=meal_type or None,
        override_headcount=override_headcount,
    )

    if request.method == "POST" and request.POST.get("confirm") == "1":
        if not rows:
            messages.warning(request, "차감할 식자재가 없습니다. 식단과 레시피를 먼저 확인해주세요.")
            return redirect("meals:deduct_inventory")

        with transaction.atomic():
            for row in rows:
                qty = row["deduct_qty"].quantize(Decimal("0.01"))
                if qty <= 0:
                    continue

                InventoryLog.objects.create(
                    ingredient=row["ingredient"],
                    log_type="출고",
                    quantity=qty,
                    description=f"{target_date} {meal_type or '전체'} 식사 완료 재고 차감",
                )

            plans = DietPlan.objects.filter(target_date=target_date)
            if meal_type:
                plans = plans.filter(meal_type=meal_type)
            plans.update(is_served=True)

        messages.success(request, f"{target_date} {meal_type or '전체'} 재고 차감이 완료되었습니다.")
        return redirect("meals:mealplan_list")

    return render(
        request,
        "meals/deduct_inventory_preview.html",
        {
            "target_date": target_date,
            "meal_type": meal_type,
            "meal_type_choices": MEAL_TYPE_CHOICES,
            "override_headcount": override_headcount or "",
            "rows": rows,
            "plan_rows": plan_rows,
            "warnings": warnings,
        },
    )
