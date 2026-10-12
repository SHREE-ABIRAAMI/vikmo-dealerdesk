from django.urls import path
from .views import SkuForecastView, ReorderSuggestionsView

urlpatterns = [
    path("forecast/<str:sku>/", SkuForecastView.as_view(), name="sku-forecast"),
    path("reorder-suggestions/", ReorderSuggestionsView.as_view(), name="reorder-suggestions"),
]
