"""Shared validation for read-only calendar/document query parameters."""
from functools import wraps
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404


def validate_month_query(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            if 'year' in request.GET and not 1 <= int(request.GET['year']) <= 9998:
                raise ValueError()
            if 'month' in request.GET and not 1 <= int(request.GET['month']) <= 12:
                raise ValueError()
        except (ValueError, TypeError):
            return HttpResponse('올바른 연도와 월(1~12)을 입력하세요.', status=400)
        return view(request, *args, **kwargs)
    return wrapped


def object_by_integer_id(model, value):
    if not str(value).isdigit() or len(str(value)) > 18:
        raise Http404('올바른 식별자가 아닙니다.')
    return get_object_or_404(model, pk=int(value))
