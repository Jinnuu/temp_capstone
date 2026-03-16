from django.shortcuts import render


def procurement_home(request):
    return render(request, "procurement/procurement_home.html")