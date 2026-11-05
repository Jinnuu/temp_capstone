from config.export_safety import literal_workbook, worksheet_title
from config.input_validation import validate_month_query
from collections import defaultdict
from datetime import date, datetime, timedelta
import calendar
import traceback
from datetime import date
from urllib.parse import urlencode

from django.contrib import messages
from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.http import HttpResponse
import openpyxl
from openpyxl.styles import Alignment, Border, Font, Side, PatternFill

from .forms import AttendancePredictionForm, PredictionFilterForm
from .models import AttendancePrediction
from .services.ingredient_calc import get_all_day_requirements
from .services.prediction_service import run_attendance_prediction
from meals.models import DietPlan
from meals.models import DietPlan, DietMenu, Menu, Recipe

MEAL_LABELS = {
    AttendancePrediction.MealType.BREAKFAST: "조식",
    AttendancePrediction.MealType.LUNCH: "중식",
    AttendancePrediction.MealType.DINNER: "석식",
}


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

            if AttendancePrediction.objects.filter(prediction_date=prediction_date, meal_type__in=meal_types).values('meal_type').distinct().count() == len(meal_types):
                messages.info(request, '해당 날짜의 조·중·석식 예측이 이미 있습니다.')
                return redirect(reverse('forecasting:prediction_list') + '?' + urlencode({'target_date': prediction_date}))

            success_count = 0
            failed_meals = []

            for meal_type in meal_types:
                if AttendancePrediction.objects.filter(prediction_date=prediction_date, meal_type=meal_type).exists():
                    continue
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
                    f"{prediction_date} 기준 예측 {success_count}건이 생성되었습니다.",
                )

                if failed_meals:
                    messages.warning(
                        request,
                        "일부 끼니 예측에 실패했습니다: " + ", ".join(failed_meals),
                    )

                url = reverse("forecasting:prediction_list")
                query_string = urlencode({"target_date": prediction_date})
                return redirect(f"{url}?{query_string}")

            messages.error(request, "예측 실행에 실패했습니다. 로그를 확인해주세요.")

            if failed_meals:
                messages.warning(request, "실패한 끼니: " + ", ".join(failed_meals))
    else:
        initial = {}
        selected_date = request.GET.get("date")

        if selected_date:
            initial["prediction_date"] = selected_date

        form = AttendancePredictionForm(initial=initial)

    return render(request, "forecasting/predict_form.html", {"form": form})


@validate_month_query
def prediction_calendar_view(request):
    today = date.today()
    selected_year = int(request.GET.get("year", today.year))
    selected_month = int(request.GET.get("month", today.month))

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.monthdatescalendar(selected_year, selected_month)

    # 해당 월의 모든 예측 데이터 조회
    predictions = AttendancePrediction.objects.filter(
        prediction_date__year=selected_year,
        prediction_date__month=selected_month,
    )

    # 날짜별로 예측 데이터 그룹화 (Key: date 객체, Value: [AttendancePrediction 객체들])
    predictions_by_date = defaultdict(list)
    for p in predictions:
        predictions_by_date[p.prediction_date].append(p)

    calendar_weeks = []
    for week in month_days:
        row = []
        for day in week:
            if day.month != selected_month:
                row.append(None)
                continue

            day_preds = predictions_by_date.get(day, [])
            has_prediction = len(day_preds) > 0
            total_count = sum(p.predicted_count for p in day_preds)

            row.append({
                "date": day,
                "day": day.day,
                "is_today": day == today,
                "has_prediction": has_prediction,
                "predictions": day_preds,  # 해당 날짜의 조식/중식/석식 예측 객체 목록
                "total_count": total_count,
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
    return render(request, "forecasting/predict_result.html", {"prediction": prediction})


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
    requirements = get_all_day_requirements(selected_date)

    context = {
        "requirements": requirements,
        "selected_date": selected_date,
        "is_all_day": True,
    }

    return render(request, "forecasting/required_ingredient_list.html", context)


def get_monday_sunday_range(date_str):
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    monday = target_date - timedelta(days=target_date.weekday())
    sunday = monday + timedelta(days=6)
    return target_date, monday, sunday


def weekly_forecast_report_view(request):
    from .services.reporting import weekly_rows
    from django.http import JsonResponse
    target_date, monday, sunday = get_monday_sunday_range(request.GET.get("date"))
    rows = weekly_rows(monday, sunday)
    if request.GET.get('format') == 'json':
        return JsonResponse({'report_items': rows})
    return render(request, "docs/weekly_forecast_report.html", {
        "target_date": target_date, "monday": monday, "sunday": sunday,
        "prev_week_date": (monday - timedelta(days=7)).isoformat(),
        "next_week_date": (monday + timedelta(days=7)).isoformat(), "report_items": rows,
    })


def export_weekly_forecast_excel(request):
    target_date, monday, sunday = get_monday_sunday_range(request.GET.get("date"))

    from .services.reporting import weekly_rows
    report_items = weekly_rows(monday, sunday)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "주간예측보고서"

    headers = ["날짜", "요일", "끼니", "식단(메뉴명)", "AI 예측 식수", "수동 예상 식수", "최종 확정 식수", "실제 식수", "예측 오차율(%)"]
    ws.append(headers)
    
    header_fill = PatternFill(start_color="F2F2F2", end_color="F2F2F2", fill_type="solid")
    header_font = Font(bold=True)
    header_border = Border(left=Side(style="thin"), right=Side(style="thin"), top=Side(style="thin"), bottom=Side(style="thin"))
    
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.border = header_border
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for item in report_items:
        ws.append([
            item['date'].isoformat(), item['weekday'], item['meal_type'], ', '.join(item['menus']),
            item['predicted_count'] if item['predicted_count'] is not None else '미생성',
            item['manual_count'], item['final_count'] if item['final_count'] is not None else '미확정',
            item['actual_count'] if item['actual_count'] is not None else '미입력',
            round(item['error_rate'], 1) if item['error_rate'] is not None else '산출 불가',
        ])

    ws.column_dimensions["A"].width = 15
    ws.column_dimensions["B"].width = 8
    ws.column_dimensions["C"].width = 10
    ws.column_dimensions["D"].width = 40
    ws.column_dimensions["E"].width = 12
    ws.column_dimensions["F"].width = 12
    ws.column_dimensions["G"].width = 16
    ws.column_dimensions["H"].width = 14
    ws.column_dimensions["I"].width = 18

    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.border = header_border
            cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.cell(row=row[0].row, column=4).alignment = Alignment(horizontal="left", vertical="center", wrap_text=True)

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    filename = f"weekly_forecast_{monday}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    literal_workbook(wb)
    wb.save(response)
    return response

