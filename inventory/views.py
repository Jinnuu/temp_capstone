from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import (
    BooleanField,
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render

from .forms import IngredientForm, InventoryLogForm
from .models import Ingredient, InventoryLog


DECIMAL_ZERO = Value(Decimal("0.00"), output_field=DecimalField(max_digits=12, decimal_places=2))


def get_ingredient_stock_queryset():
    return (
        Ingredient.objects.all()
        .annotate(
            in_qty=Coalesce(
                Sum(
                    Case(
                        When(inventorylog__log_type=InventoryLog.LogType.IN, then=F("inventorylog__quantity")),
                        default=DECIMAL_ZERO,
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                DECIMAL_ZERO,
            ),
            out_qty=Coalesce(
                Sum(
                    Case(
                        When(inventorylog__log_type=InventoryLog.LogType.OUT, then=F("inventorylog__quantity")),
                        default=DECIMAL_ZERO,
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                DECIMAL_ZERO,
            ),
            waste_qty=Coalesce(
                Sum(
                    Case(
                        When(inventorylog__log_type=InventoryLog.LogType.WASTE, then=F("inventorylog__quantity")),
                        default=DECIMAL_ZERO,
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                DECIMAL_ZERO,
            ),
        )
        .annotate(
            current_stock=ExpressionWrapper(
                F("in_qty") - F("out_qty") - F("waste_qty"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )
        .annotate(
            is_low_stock=Case(
                When(current_stock__lte=F("safe_stock_level"), then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )
        .order_by("id")
    )


def get_current_stock(ingredient_id):
    ingredient = get_ingredient_stock_queryset().get(pk=ingredient_id)
    return ingredient.current_stock


def ingredient_list(request):
    selected_category = request.GET.get("category", "").strip()

    ingredients = get_ingredient_stock_queryset()

    if selected_category:
        ingredients = ingredients.filter(category=selected_category)

    categories = (
        Ingredient.objects.exclude(category__isnull=True)
        .exclude(category__exact="")
        .values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    paginator = Paginator(ingredients, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "categories": categories,
        "selected_category": selected_category,
    }
    return render(request, "inventory/ingredient_list.html", context)


def ingredient_create(request):
    if request.method == "POST":
        form = IngredientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("inventory:ingredient_list")
    else:
        form = IngredientForm()

    return render(request, "inventory/ingredient_form.html", {"form": form})


def inventory_log_create(request):
    if request.method == "POST":
        form = InventoryLogForm(request.POST)
        if form.is_valid():
            ingredient = form.cleaned_data["ingredient"]
            log_type = form.cleaned_data["log_type"]
            quantity = form.cleaned_data["quantity"]

            if log_type in [InventoryLog.LogType.OUT, InventoryLog.LogType.WASTE]:
                current_stock = get_current_stock(ingredient.id)
                if quantity > current_stock:
                    form.add_error(
                        "quantity",
                        f"현재 재고({current_stock})보다 많은 수량은 출고/폐기할 수 없습니다.",
                    )

            if form.is_valid():
                form.save()
                return redirect("inventory:ingredient_list")
    else:
        form = InventoryLogForm()

    return render(request, "inventory/inventory_log_form.html", {"form": form})