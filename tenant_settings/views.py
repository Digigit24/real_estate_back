from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from common.mixins import TenantViewSetMixin
from common.permissions import JWTAuthentication, HasCRMPermission
from .models import TenantSettings, PaymentPlanTemplate
from .serializers import (
    TenantSettingsSerializer, PaymentPlanTemplateSerializer,
    PaymentPlanPreviewSerializer, PaymentPlanPreviewResponseSerializer,
)


class TenantSettingsView(APIView):
    """
    GET  /api/tenant/settings/  — get current tenant's white-label settings (creates defaults if missing)
    PUT  /api/tenant/settings/  — update settings
    PATCH /api/tenant/settings/ — partial update
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'settings'

    def _get_or_create(self, tenant_id):
        obj, _ = TenantSettings.objects.get_or_create(tenant_id=tenant_id)
        return obj

    @extend_schema(description='Get white-label and branding settings for this tenant')
    def get(self, request):
        obj = self._get_or_create(request.tenant_id)
        return Response(TenantSettingsSerializer(obj).data)

    @extend_schema(
        description='Update all branding/settings fields (full replace)',
        request=TenantSettingsSerializer,
        responses={200: TenantSettingsSerializer},
    )
    def put(self, request):
        obj = self._get_or_create(request.tenant_id)
        serializer = TenantSettingsSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        description='Partially update branding/settings fields (send only fields you want to change)',
        request=TenantSettingsSerializer,
        responses={200: TenantSettingsSerializer},
    )
    def patch(self, request):
        obj = self._get_or_create(request.tenant_id)
        serializer = TenantSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class PaymentPlanTemplateViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    CRUD for reusable payment plan templates per tenant.

    Special actions:
    - POST /{id}/set-default/ — mark this template as the default for new bookings
    - POST /apply/            — apply a template to generate milestone data (preview)
    """
    queryset = PaymentPlanTemplate.objects.all()
    serializer_class = PaymentPlanTemplateSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'payment_plan_templates'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_default', 'plan_type']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        serializer.save(tenant_id=tenant_id, owner_user_id=self.request.user_id)

    @extend_schema(
        description='Mark this template as the default for new bookings (unsets previous default). No request body needed.',
        request=None,
        responses={200: PaymentPlanTemplateSerializer},
    )
    @action(detail=True, methods=['post'], url_path='set-default')
    def set_default(self, request, pk=None):
        template = self.get_object()
        PaymentPlanTemplate.objects.filter(
            tenant_id=request.tenant_id, is_default=True
        ).exclude(id=template.id).update(is_default=False)
        template.is_default = True
        template.save(update_fields=['is_default', 'updated_at'])
        return Response(PaymentPlanTemplateSerializer(template).data)

    @extend_schema(
        description='Preview computed milestone dates and amounts for a given booking date and total booking amount.',
        request=PaymentPlanPreviewSerializer,
        responses={
            200: PaymentPlanPreviewResponseSerializer,
            400: {'description': 'Missing template_id, booking_date, or total_amount'},
            404: {'description': 'Template not found for this tenant'},
        },
    )
    @action(detail=False, methods=['post'], url_path='preview')
    def preview(self, request):
        from datetime import date, timedelta
        from decimal import Decimal

        template_id = request.data.get('template_id')
        booking_date_str = request.data.get('booking_date')
        total_amount = request.data.get('total_amount')

        if not all([template_id, booking_date_str, total_amount]):
            return Response(
                {'error': 'template_id, booking_date, and total_amount are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            template = PaymentPlanTemplate.objects.get(id=template_id, tenant_id=request.tenant_id)
        except PaymentPlanTemplate.DoesNotExist:
            return Response({'error': 'Template not found'}, status=status.HTTP_404_NOT_FOUND)

        booking_date = date.fromisoformat(booking_date_str)
        total = Decimal(str(total_amount))
        milestones = []
        for i, stage in enumerate(template.stages):
            pct = Decimal(str(stage['percentage']))
            amt = (total * pct / 100).quantize(Decimal('0.01'))
            due = booking_date + timedelta(days=stage['days_from_booking'])
            milestones.append({
                'order_index': i,
                'milestone_name': stage['name'],
                'percentage': pct,
                'amount': amt,
                'due_date': due,
            })
        return Response({
            'template_id': template.id,
            'template_name': template.name,
            'total_amount': total,
            'milestones': milestones,
        })
