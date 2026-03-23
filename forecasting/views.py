from django.shortcuts import render


def forecasting_home(request):
    return render(request, "forecasting/forecasting_home.html")
