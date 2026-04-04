from django.urls import path
from . import views

urlpatterns = [
    path("", views.order_list, name="procurement_home"),
    path("orders/", views.order_list, name="procurement_order_list"),
    path("create/", views.order_create, name="procurement_order_create"),
    path("orders/<int:pk>/", views.order_detail, name="procurement_order_detail"),
]