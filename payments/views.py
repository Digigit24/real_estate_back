from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .models import Payment
from .serializers import PaymentSerializer, PaymentListSerializer, PaymentHistorySerializer
from common.mixins import TenantViewSetMixin


@extend_schema_view(
    list=extend_schema(description='List all payments'),
    retrieve=extend_schema(description='Retrieve a specific payment'),
    create=extend_schema(description='Create a new payment'),
    update=extend_schema(description='Update a payment'),
    partial_update=extend_schema(description='Partially update a payment'),
    destroy=extend_schema(description='Delete a payment'),
)
class PaymentViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing Payments
    """
    queryset = Payment.objects.select_related('lead')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'lead': ['exact'],
        'type': ['exact'],
        'status': ['exact'],
        'date': ['gte', 'lte', 'exact'],
        'due_date': ['gte', 'lte', 'exact'],
        'amount': ['gte', 'lte', 'exact'],
        'currency': ['exact'],
        'created_at': ['gte', 'lte'],
    }
    search_fields = ['reference_no', 'method', 'notes', 'lead__name']
    ordering_fields = ['date', 'due_date', 'amount', 'created_at']
    ordering = ['-date']

    def get_serializer_class(self):
        """Use lighter serializer for list view"""
        if self.action == 'list':
            return PaymentListSerializer
        if self.action == 'history':
            return PaymentHistorySerializer
        return PaymentSerializer

    @extend_schema(
        description='Return payment history table for a lead, ordered by date descending.',
        parameters=[
            OpenApiParameter(
                name='lead',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by lead ID',
            ),
        ],
        responses=PaymentHistorySerializer(many=True),
    )
    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request, *args, **kwargs):
        """
        Returns payment history rows: date, due_date, total, currency, status.
        Supports optional ?lead=<id> query parameter.
        """
        queryset = self.filter_queryset(self.get_queryset())
        lead_id = request.query_params.get('lead')
        if lead_id:
            queryset = queryset.filter(lead_id=lead_id)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PaymentHistorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = PaymentHistorySerializer(queryset, many=True)
        return Response(serializer.data)
