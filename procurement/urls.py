from django.urls import path
from . import views

app_name = "procurement"

urlpatterns = [
    path("", views.order_list, name="home"),
    path("orders/", views.order_list, name="order_list"),
    path("create/", views.order_create, name="order_create"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
]