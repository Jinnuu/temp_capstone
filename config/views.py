import calendar
from datetime import date, datetime

from django.shortcuts import render

from forecasting.models import AttendancePrediction
from inventory.views import get_ingredient_stock_queryset
from meals.models import DietPlan
from procurement.models import PurchaseOrder


MEAL_KEY_MAP = {
    "조식": "breakfast",
    "중식": "lunch",
    "석식": "dinner",
}

MEAL_LABEL_MAP = {
    "breakfast": "조식",
    "lunch": "중식",
    "dinner": "석식",
}


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_date(value, default):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return default


def home(request):
    today = date.today()

    selected_year = _parse_int(request.GET.get("year"), today.year)
    selected_month = _parse_int(request.GET.get("month"), today.month)

    if selected_month < 1 or selected_month > 12:
        selected_month = today.month

    selected_date = _parse_date(request.GET.get("date"), today)

    if selected_date.year != selected_year or selected_date.month != selected_month:
        selected_year = selected_date.year
        selected_month = selected_date.month

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

        meal_key = MEAL_KEY_MAP.get(plan.meal_type)
        if not meal_key:
            continue

        meal_map[day][meal_key] = [
            item.menu.name for item in plan.diet_menus.all()
        ]

    predictions = AttendancePrediction.objects.filter(
        prediction_date__year=selected_year,
        prediction_date__month=selected_month,
    ).order_by("prediction_date", "meal_type", "-created_at")

    prediction_map = {}

    for prediction in predictions:
        day = prediction.prediction_date.day
        prediction_map.setdefault(day, {})

        if prediction.meal_type not in prediction_map[day]:
            prediction_map[day][prediction.meal_type] = prediction.predicted_count

    calendar_weeks = []
    month_calendar = calendar.Calendar(firstweekday=calendar.SUNDAY)

    for week in month_calendar.monthdayscalendar(selected_year, selected_month):
        week_cells = []

        for day_num in week:
            if day_num == 0:
                week_cells.append(None)
                continue

            cell_date = date(selected_year, selected_month, day_num)

            meals = meal_map.get(
                day_num,
                {
                    "breakfast": [],
                    "lunch": [],
                    "dinner": [],
                },
            )

            prediction_values = prediction_map.get(day_num, {})

            week_cells.append(
                {
                    "day": day_num,
                    "date": cell_date,
                    "is_today": cell_date == today,
                    "is_selected": cell_date == selected_date,
                    "meals": meals,
                    "predictions": prediction_values,
                    "has_meal": bool(
                        meals["breakfast"] or meals["lunch"] or meals["dinner"]
                    ),
                    "has_prediction": bool(prediction_values),
                }
            )

        calendar_weeks.append(week_cells)

    selected_plans = (
        DietPlan.objects.filter(target_date=selected_date)
        .prefetch_related("diet_menus__menu")
        .order_by("meal_type")
    )

    selected_predictions = AttendancePrediction.objects.filter(
        prediction_date=selected_date
    ).order_by("meal_type", "-created_at")

    selected_prediction_rows = []
    used_meal_types = set()

    for prediction in selected_predictions:
        if prediction.meal_type in used_meal_types:
            continue

        used_meal_types.add(prediction.meal_type)
        selected_prediction_rows.append(
            {
                "meal_type": prediction.meal_type,
                "meal_label": prediction.get_meal_type_display(),
                "predicted_count": prediction.predicted_count,
            }
        )

    low_stock_items = list(
        get_ingredient_stock_queryset()
        .filter(is_low_stock=True)
        .order_by("calc_stock", "name")[:8]
    )

    pending_order_count = PurchaseOrder.objects.filter(
        status=PurchaseOrder.Status.PENDING
    ).count()

    context = {
        "today": today,
        "selected_year": selected_year,
        "selected_month": selected_month,
        "selected_date": selected_date,
        "years": range(today.year - 1, today.year + 2),
        "months": range(1, 13),
        "calendar_weeks": calendar_weeks,
        "selected_plans": selected_plans,
        "selected_prediction_rows": selected_prediction_rows,
        "low_stock_items": low_stock_items,
        "pending_order_count": pending_order_count,
        "meal_label_map": MEAL_LABEL_MAP,
    }

    return render(request, "home.html", context)


def docs_index(request):
    # 기존 config/urls.py의 docs_index import 오류 방지용.
    # 실제 데이터 문서화 기능은 다른 팀원 작업과 합칠 예정이므로 화면에서는 사용하지 않는다.
    return render(request, "home.html")