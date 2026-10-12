from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .services import ForecastingService
from core.exceptions import NotFoundError


class SkuForecastView(APIView):
    def get(self, request, sku):
        forecast = ForecastingService.get_sku_forecast(sku)
        if forecast is None:
            raise NotFoundError(f"Forecast for SKU '{sku}' not found.")

        return Response(
            {"sku": sku, "forecast": forecast},
            status=status.HTTP_200_OK
        )


class ReorderSuggestionsView(APIView):
    def get(self, request):
        results = ForecastingService.get_reorder_suggestions()
        return Response(
            {"results": results},
            status=status.HTTP_200_OK
        )
