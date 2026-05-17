from datetime import date, datetime
import calendar
from urllib.parse import urlencode
import traceback

from django.contrib import messages
from django.db.models import Case, When, Value, IntegerField
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import AttendancePredictionForm, PredictionFilterForm
from .models import AttendancePrediction
from .services.ingredient_calc import get_ingredient_requirements
from .services.prediction_service import run_attendance_prediction
from .services.ingredient_calc import get_all_day_requirements


def forecasting_home(request):
    return redirect("forecasting:prediction_create")


def prediction_create_view(request):
    if request.method == "POST":
        form = AttendancePredictionForm(request.POST)
        if form.is_valid():
            prediction_date = form.cleaned_data["prediction_date"]

            meal_types = [
                AttendancePrediction.MealType.BREAKFAST,
                AttendancePrediction.MealType.LUNCH,
                AttendancePrediction.MealType.DINNER,
            ]

            success_count = 0
            failed_meals = []

            for meal_type in meal_types:
                try:
                    run_attendance_prediction(
                        prediction_date=prediction_date,
                        meal_type=meal_type,
                        menu_text=None,
                    )
                    success_count += 1
                except Exception as e:
                    traceback.print_exc()
                    failed_meals.append(f"{meal_type}({e})")

            if success_count:
                messages.success(
                    request,
                    f"{prediction_date} 기준 예측 {success_count}건이 생성되었습니다."
                )

                if failed_meals:
                    messages.warning(
                        request,
                        "일부 끼니 예측에 실패했습니다: " + ", ".join(failed_meals)
                    )

                url = reverse("forecasting:prediction_list")
                query_string = urlencode({"target_date": prediction_date})
                return redirect(f"{url}?{query_string}")

            messages.error(
                request,
                "예측 실행에 실패했습니다. 로그를 확인해주세요."
            )

            if failed_meals:
                messages.warning(
                    request,
                    "실패한 끼니: " + ", ".join(failed_meals)
                )
    else:
        initial = {}
        selected_date = request.GET.get("date")
        if selected_date:
            initial["prediction_date"] = selected_date
        form = AttendancePredictionForm(initial=initial)

    return render(request, "forecasting/predict_form.html", {"form": form})

def prediction_calendar_view(request):
    today = date.today()
    selected_year = int(request.GET.get("year", today.year))
    selected_month = int(request.GET.get("month", today.month))

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdatescalendar(selected_year, selected_month)

    predictions = AttendancePrediction.objects.filter(
        prediction_date__year=selected_year,
        prediction_date__month=selected_month,
    )
    predicted_dates = {p.prediction_date for p in predictions}

    calendar_weeks = []
    for week in month_days:
        row = []
        for day in week:
            if day.month != selected_month:
                row.append(None)
                continue

            has_prediction = day in predicted_dates
            row.append({
                "date": day,
                "day": day.day,
                "is_today": day == today,
                "has_prediction": has_prediction,
                "status_label": "결과 있음" if has_prediction else "미생성",
            })
        calendar_weeks.append(row)

    context = {
        "selected_year": selected_year,
        "selected_month": selected_month,
        "months": range(1, 13),
        "calendar_weeks": calendar_weeks,
    }
    return render(request, "forecasting/prediction_calendar.html", context)

def prediction_result_view(request, prediction_id):
    prediction = get_object_or_404(AttendancePrediction, id=prediction_id)
    return render(
        request,
        "forecasting/predict_result.html",
        {"prediction": prediction},
    )


def prediction_list_view(request):
    form = PredictionFilterForm(request.GET or None)

    predictions = AttendancePrediction.objects.annotate(
        meal_order=Case(
            When(meal_type=AttendancePrediction.MealType.BREAKFAST, then=Value(1)),
            When(meal_type=AttendancePrediction.MealType.LUNCH, then=Value(2)),
            When(meal_type=AttendancePrediction.MealType.DINNER, then=Value(3)),
            default=Value(99),
            output_field=IntegerField(),
        )
    )

    if form.is_valid():
        target_date = form.cleaned_data.get("target_date")
        start_date = form.cleaned_data.get("start_date")
        end_date = form.cleaned_data.get("end_date")
        order = form.cleaned_data.get("order") or "latest"

        if target_date:
            predictions = predictions.filter(prediction_date=target_date)
        else:
            if start_date:
                predictions = predictions.filter(prediction_date__gte=start_date)
            if end_date:
                predictions = predictions.filter(prediction_date__lte=end_date)

        if order == "oldest":
            predictions = predictions.order_by("prediction_date", "meal_order", "created_at")
        else:
            predictions = predictions.order_by("-prediction_date", "meal_order", "-created_at")
    else:
        predictions = predictions.order_by("-prediction_date", "meal_order", "-created_at")

    return render(
        request,
        "forecasting/prediction_list.html",
        {
            "predictions": predictions,
            "form": form,
        },
    )


def ingredient_requirement_view(request):
    selected_date = request.GET.get("date", date.today().isoformat())
    
    # 💥 날짜 전체 통합 데이터 호출
    requirements = get_all_day_requirements(selected_date)

    context = {
        "requirements": requirements,
        "selected_date": selected_date,
        "is_all_day": True, # 템플릿 표시용
    }
    return render(request, "forecasting/required_ingredient_list.html", context)

