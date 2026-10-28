from django.urls import path
from . import views
from .views_new_docs import doc_purchase_requisition, doc_inspection_log, doc_cooking_instruction

app_name = "procurement"

urlpatterns = [
    path("", views.order_list, name="home"),
    path("orders/", views.order_list, name="order_list"),
    path("create/", views.order_create, name="order_create"),
    path("create-smart/", views.order_from_mealplan, name="order_from_mealplan"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/status/", views.order_status_update, name="order_status_update"),

    # Reports (기존)
    path("weekly-report/", views.weekly_procurement_report, name="weekly_procurement_report"),
    path("vendor-report/", views.vendor_procurement_report, name="vendor_procurement_report"),
    path("daily-report/", views.daily_inspection_report, name="daily_inspection_report"),
    path("weekly-report/excel/", views.export_weekly_procurement_excel, name="export_weekly_procurement_excel"),
    path("vendor-report/excel/", views.export_vendor_procurement_excel, name="export_vendor_procurement_excel"),
    path("daily-report/excel/", views.export_daily_inspection_excel, name="export_daily_inspection_excel"),

    # [신규] 실무 문서 양식
    path("docs/purchase-requisition/", doc_purchase_requisition, name="doc_purchase_requisition"),
    path("docs/inspection-log/", doc_inspection_log, name="doc_inspection_log"),
    path("docs/cooking-instruction/", doc_cooking_instruction, name="doc_cooking_instruction"),
    path("docs/monthly-settlement/", views.monthly_settlement_view, name="doc_monthly_settlement"),
    path("monthly-settlement/", views.monthly_settlement_view, name="monthly_settlement_view"),

    # [신규] 거래처(발주 업체) 관리
    path("suppliers/", views.supplier_list, name="supplier_list"),
    path("suppliers/create/", views.supplier_create, name="supplier_create"),
    path("suppliers/<int:pk>/update/", views.supplier_update, name="supplier_update"),
    path("suppliers/<int:pk>/delete/", views.supplier_delete, name="supplier_delete"),
]
