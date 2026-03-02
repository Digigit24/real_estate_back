from django.db.models import Sum, Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.mixins import TenantViewSetMixin
from common.permissions import JWTAuthentication, HasCRMPermission
from .models import Broker, Commission, CommissionStatusEnum, BrokerStatusEnum
from .serializers import (
    BrokerSerializer, BrokerListSerializer,
    CommissionSerializer, CommissionCreateSerializer, CommissionMarkPaidSerializer,
)
import logging

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(description='List all channel partners / brokers'),
    retrieve=extend_schema(description='Get broker detail with leads and commissions summary'),
    create=extend_schema(description='Register a new broker'),
    update=extend_schema(description='Update broker details'),
    partial_update=extend_schema(description='Partially update broker details'),
    destroy=extend_schema(description='Delete a broker'),
)
class BrokerViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for Channel Partner / Broker management.

    Special actions:
    - GET  /leaderboard/        — broker leaderboard sorted by bookings/commissions
    - GET  /{id}/leads/         — leads submitted by this broker
    - GET  /{id}/commissions/   — commissions for this broker
    """
    queryset = Broker.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'brokers'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'city']
    search_fields = ['name', 'phone', 'email', 'company_name', 'rera_number']
    ordering_fields = ['name', 'created_at', 'commission_rate']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return BrokerListSerializer
        return BrokerSerializer

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        serializer.save(tenant_id=tenant_id, owner_user_id=self.request.user_id)

    @extend_schema(description='Broker leaderboard: sorted by bookings count and total commission')
    @action(detail=False, methods=['get'], url_path='leaderboard')
    def leaderboard(self, request):
        tenant_id = request.tenant_id
        brokers = Broker.objects.filter(
            tenant_id=tenant_id,
            status=BrokerStatusEnum.ACTIVE,
        ).annotate(
            bookings_count=Count('commissions', filter=Q(commissions__status__in=[
                CommissionStatusEnum.PENDING, CommissionStatusEnum.PAID
            ])),
            total_commission=Sum('commissions__commission_amount', filter=Q(
                commissions__status__in=[CommissionStatusEnum.PENDING, CommissionStatusEnum.PAID]
            )),
            leads_count=Count('id'),  # placeholder; real count done via CRM
        ).order_by('-bookings_count', '-total_commission')

        data = []
        for rank, broker in enumerate(brokers, start=1):
            from crm.models import Lead
            leads_count = Lead.objects.filter(tenant_id=tenant_id, broker_id=broker.id).count()
            data.append({
                'rank': rank,
                'broker_id': broker.id,
                'name': broker.name,
                'phone': broker.phone,
                'company_name': broker.company_name,
                'bookings_count': broker.bookings_count or 0,
                'total_commission': broker.total_commission or 0,
                'leads_count': leads_count,
            })
        return Response({'count': len(data), 'results': data})

    @extend_schema(description='Get all leads submitted / attributed to this broker')
    @action(detail=True, methods=['get'], url_path='leads')
    def leads(self, request, pk=None):
        broker = self.get_object()
        from crm.models import Lead
        from crm.serializers import LeadListSerializer
        leads = Lead.objects.filter(
            tenant_id=request.tenant_id,
            broker_id=broker.id,
        ).select_related('status')
        return Response(LeadListSerializer(leads, many=True, context={'request': request}).data)

    @extend_schema(description='Get all commissions for this broker')
    @action(detail=True, methods=['get'], url_path='commissions')
    def broker_commissions(self, request, pk=None):
        broker = self.get_object()
        commissions = broker.commissions.select_related(
            'booking', 'booking__unit', 'booking__unit__tower', 'booking__unit__tower__project'
        ).all()
        return Response(CommissionSerializer(commissions, many=True).data)


@extend_schema_view(
    list=extend_schema(description='List all commissions'),
    retrieve=extend_schema(description='Get commission detail'),
    create=extend_schema(description='Create a commission record for a broker booking'),
    update=extend_schema(description='Update commission details'),
    partial_update=extend_schema(description='Partially update commission'),
    destroy=extend_schema(description='Delete a commission record'),
)
class CommissionViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for Commission management.

    Special actions:
    - POST /{id}/mark-paid/ — mark commission as paid
    """
    queryset = Commission.objects.select_related(
        'broker', 'booking', 'booking__unit', 'booking__unit__tower', 'booking__unit__tower__project'
    ).all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'commissions'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'status': ['exact', 'in'],
        'broker': ['exact'],
        'booking': ['exact'],
    }
    ordering_fields = ['created_at', 'commission_amount', 'paid_date']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return CommissionCreateSerializer
        return CommissionSerializer

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        serializer.save(tenant_id=tenant_id, owner_user_id=self.request.user_id)

    @extend_schema(
        description='Mark commission as paid',
        request=CommissionMarkPaidSerializer,
    )
    @action(detail=True, methods=['post'], url_path='mark-paid')
    def mark_paid(self, request, pk=None):
        commission = self.get_object()
        serializer = CommissionMarkPaidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        commission.status = CommissionStatusEnum.PAID
        commission.paid_date = serializer.validated_data['paid_date']
        if serializer.validated_data.get('notes'):
            commission.notes = serializer.validated_data['notes']
        commission.save(update_fields=['status', 'paid_date', 'notes', 'updated_at'])
        return Response(CommissionSerializer(commission).data)
