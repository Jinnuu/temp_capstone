from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .forms import AttendancePredictionForm
from .models import AttendancePrediction
from .services.prediction_service import run_attendance_prediction
import traceback

from datetime import timedelta
from django.utils import timezone

def forecasting_home(request):
    tomorrow = timezone.localdate() + timedelta(days=1)
    return render(
        request,
        "forecasting/forecasting_home.html",
        {"tomorrow": tomorrow},
    )


def prediction_create_view(request):
    if request.method == "POST":
        form = AttendancePredictionForm(request.POST)
        if form.is_valid():
            prediction_date = form.cleaned_data["prediction_date"]
            meal_type = form.cleaned_data["meal_type"]

            try:
                prediction = run_attendance_prediction(
                    prediction_date=prediction_date,
                    meal_type=meal_type,
                    menu_text=None,
                )
                return redirect("forecasting:prediction_result", prediction_id=prediction.id)
            except Exception as e:
                traceback.print_exc()
                messages.error(request, f"예측 실행 중 오류가 발생했습니다: {e}")
    else:
        form = AttendancePredictionForm()

    return render(request, "forecasting/predict_form.html", {"form": form})


def prediction_result_view(request, prediction_id):
    prediction = get_object_or_404(AttendancePrediction, id=prediction_id)
    return render(
        request,
        "forecasting/predict_result.html",
        {"prediction": prediction},
    )


def prediction_list_view(request):
    predictions = AttendancePrediction.objects.all()
    return render(
        request,
        "forecasting/prediction_list.html",
        {"predictions": predictions},
    )