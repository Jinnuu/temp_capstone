"""One read model for HTML, JSON and Excel; never invent observed attendance."""
from meals.models import DietPlan
from forecasting.models import AttendancePrediction

MEALS = {'breakfast': '조식', 'lunch': '중식', 'dinner': '석식'}


def weekly_rows(monday, sunday):
    predictions = {}
    for prediction in AttendancePrediction.objects.filter(
        prediction_date__range=(monday, sunday)
    ).order_by('-created_at', '-pk'):
        predictions.setdefault((prediction.prediction_date, MEALS.get(prediction.meal_type)), prediction.predicted_count)
    plans = list(DietPlan.objects.filter(target_date__range=(monday, sunday))
                 .select_related('forecast').prefetch_related('diet_menus__menu'))
    order = {'조식': 1, '중식': 2, '석식': 3}
    plans.sort(key=lambda p: (p.target_date, order.get(p.meal_type, 99), p.pk))
    rows = []
    for plan in plans:
        predicted = predictions.get((plan.target_date, plan.meal_type))
        forecast = getattr(plan, 'forecast', None)
        actual = forecast.actual_count if forecast else None
        # Legacy negative observations are invalid; do not use them for accuracy.
        invalid_actual = actual is not None and actual < 0
        if invalid_actual:
            actual = None
        error = ((predicted - actual) / actual) * 100 if predicted is not None and actual is not None and actual > 0 else None
        same_day = [p for p in plans if p.target_date == plan.target_date]
        rows.append({'date': plan.target_date, 'weekday': '월화수목금토일'[plan.target_date.weekday()],
                     'meal_type': plan.meal_type, 'menus': [dm.menu.name for dm in plan.diet_menus.all()],
                     'predicted_count': predicted, 'manual_count': plan.headcount,
                     'final_count': plan.final_headcount, 'actual_count': actual,
                     'invalid_actual': invalid_actual, 'error_rate': error,
                     'is_first_of_day': plan.pk == same_day[0].pk, 'day_span': len(same_day)})
    return rows
