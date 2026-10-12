from django.urls import path
from .views import DealerListCreateView, DealerDetailView

urlpatterns = [
    path("dealers/", DealerListCreateView.as_view(), name="dealer-list-create"),
    path("dealers/<int:pk>/", DealerDetailView.as_view(), name="dealer-detail"),
]
