from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Dealer
from .serializers import DealerSerializer, DealerCreateSerializer
from core.pagination import StandardResultsSetPagination
from core.exceptions import NotFoundError, ValidationError, DuplicateError


class DealerListCreateView(APIView):
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        queryset = Dealer.objects.all().order_by("id")
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        serializer = DealerSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = DealerCreateSerializer(data=request.data)
        if not serializer.is_valid():
            errors = serializer.errors
            if "dealer_code" in errors:
                for err in errors["dealer_code"]:
                    if "already exists" in str(err).lower():
                        raise DuplicateError(str(err))
            raise ValidationError(message="Validation failed.", details=errors)

        dealer = serializer.save()
        out_serializer = DealerSerializer(dealer)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)


class DealerDetailView(APIView):
    def get(self, request, pk):
        try:
            dealer = Dealer.objects.get(pk=pk)
        except (Dealer.DoesNotExist, ValueError):
            raise NotFoundError(f"Dealer with id {pk} not found.")

        serializer = DealerSerializer(dealer)
        return Response(serializer.data, status=status.HTTP_200_OK)
