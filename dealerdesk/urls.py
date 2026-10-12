from django.contrib import admin
from django.urls import include, path
from core.views import portal

urlpatterns = [
    path("", portal, name="dealer-portal"),
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
    path("api/", include("products.urls")),
    path("api/", include("dealers.urls")),
    path("api/", include("orders.urls")),
    path("api/", include("forecasting.urls")),
    path("api/", include("assistant.urls")),
    path("api/", include("supplier.urls")),
]
