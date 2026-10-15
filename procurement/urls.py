from . import workflow_views as workflow
from .views_new_docs import doc_purchase_requisition, doc_inspection_log
from django.urls import path

from . import views

app_name = "procurement"

urlpatterns = [
    path("", views.order_list, name="home"),
    path("orders/", views.order_list, name="order_list"),
    path("create/", views.order_create, name="order_create"),
    path("create-smart/", views.order_from_mealplan, name="order_from_mealplan"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/status/", views.order_status_update, name="order_status_update"),

    path("weekly-report/", views.weekly_procurement_report, name="weekly_procurement_report"),
    path("vendor-report/", views.vendor_procurement_report, name="vendor_procurement_report"),
    path("daily-report/", views.daily_inspection_report, name="daily_inspection_report"),
    path("weekly-report/excel/", views.export_weekly_procurement_excel, name="export_weekly_procurement_excel"),
    path("vendor-report/excel/", views.export_vendor_procurement_excel, name="export_vendor_procurement_excel"),
    path("daily-report/excel/", views.export_daily_inspection_excel, name="export_daily_inspection_excel"),
    path("docs/purchase-requisition/", doc_purchase_requisition, name="doc_purchase_requisition"),
    path("docs/inspection-log/", doc_inspection_log, name="doc_inspection_log"),
]

urlpatterns += [
    path("workflow/", workflow.hub, name="workflow"),
    path("workflow/preview/", workflow.preview, name="workflow_preview"),
    path("workflow/plans/<int:pk>/", workflow.plan_detail, name="workflow_plan"),
    path("workflow/inspections/", workflow.inspections, name="workflow_inspections"),
    path("workflow/inspections/<int:pk>/", workflow.inspection, name="workflow_inspection"),
    path("workflow/transactions/", workflow.stock_transaction, name="workflow_transaction"),
    path("workflow/ledger/", workflow.ledger, name="workflow_ledger"),
    path("workflow/settlement/", workflow.settlement, name="workflow_settlement"),
    path("workflow/specs/", workflow.specifications, name="workflow_specs"),
    path("workflow/specs/<int:pk>/", workflow.specifications, name="workflow_spec_edit"),
    path("workflow/suppliers/", workflow.suppliers, name="workflow_suppliers"),
    path("workflow/suppliers/<int:pk>/", workflow.suppliers, name="workflow_supplier_edit"),
    path("workflow/categories/", workflow.categories, name="workflow_categories"),
    path("workflow/recipes/", workflow.recipe_detail, name="workflow_recipes"),
    path("workflow/recipes/<int:pk>/", workflow.recipe_detail, name="workflow_recipe_edit"),
]
