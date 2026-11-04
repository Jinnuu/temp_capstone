from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from .views import docs_index, home

urlpatterns = [
    path("ui/compare/", TemplateView.as_view(template_name="ui/compare.html"), name="ui_compare"),
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("docs/", docs_index, name="docs_index"),
    path("accounts/", include("accounts.urls")),
    path("inventory/", include("inventory.urls")),
    path("meals/", include("meals.urls")),
    path("forecasting/", include("forecasting.urls")),
    path("procurement/", include("procurement.urls")),
]
