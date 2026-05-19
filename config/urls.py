from django.contrib import admin
from django.urls import include, path
from .views import home
urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("inventory/", include("inventory.urls")),
    path("meals/", include("meals.urls")),
    path("forecasting/", include("forecasting.urls")),
    path("procurement/", include("procurement.urls")),
]
#ttttt