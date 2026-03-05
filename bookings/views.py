from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from common.mixins import TenantViewSetMixin
from tenant_settings.models import TenantSettings
from common.permissions import JWTAuthentication, HasCRMPermission
from inventory.models import UnitStatusEnum
from .models import Booking, PaymentMilestone, PaymentPlanTypeEnum, MilestoneStatusEnum, BookingStatusEnum
from .serializers import (
    BookingSerializer, BookingListSerializer, BookingCreateSerializer,
    PaymentMilestoneSerializer, MilestoneMarkPaidSerializer,
)
import logging

logger = logging.getLogger(__name__)


def _get_builder_info(tenant_id):
    """Return tenant branding/contact info for PDF documents."""
    try:
        s = TenantSettings.objects.get(tenant_id=tenant_id)
        return {
            'company_name': s.company_name,
            'logo_url': s.logo_url,
            'gstin': s.gstin,
            'address': s.address,
            'city': s.city,
            'state': s.state,
            'pincode': s.pincode,
            'support_email': s.support_email,
            'support_phone': s.support_phone,
            'pdf_header_text': s.pdf_header_text,
            'pdf_footer_text': s.pdf_footer_text,
            'signature_url': s.signature_url,
        }
    except TenantSettings.DoesNotExist:
        return {}


def _auto_create_commission(booking, tenant_id):
    """
    If the booked lead was referred by a broker, auto-create a Commission record
    using the broker's default commission_rate.
    """
    try:
        from crm.models import Lead
        lead = Lead.objects.get(id=booking.lead_id)
        if not lead.broker_id:
            return
        from brokers.models import Broker, Commission
        broker = Broker.objects.get(id=lead.broker_id, tenant_id=tenant_id)
        commission_amount = (booking.total_amount * broker.commission_rate / 100).quantize(Decimal('0.01'))
        Commission.objects.get_or_create(
            booking=booking,
            broker=broker,
            defaults=dict(
                tenant_id=tenant_id,
                lead_id=lead.id,
                commission_rate=broker.commission_rate,
                commission_amount=commission_amount,
                owner_user_id=booking.owner_user_id,
            )
        )
        logger.info(f"Auto-created commission for broker {broker.id} on booking #{booking.id}")
    except Exception as e:
        logger.warning(f"Auto-commission skipped for booking #{booking.id}: {e}")


def _generate_20_80_milestones(booking, total_amount):
    """
    20:80 Plan:
      - 10% Token       — booking date
      - 10% Agreement   — booking + 30 days
      - 80% Possession  — possession date from project (or booking + 730 days fallback)
    """
    possession_date = None
    try:
        possession_date = booking.unit.tower.project.possession_date
    except Exception:
        pass
    if not possession_date:
        possession_date = booking.booking_date + timedelta(days=730)

    milestones = [
        dict(name='Token Amount', pct=Decimal('10'), days_offset=0),
        dict(name='Agreement / Booking Amount', pct=Decimal('10'), days_offset=30),
        dict(name='On Possession', pct=Decimal('80'), date=possession_date),
    ]
    result = []
    for i, m in enumerate(milestones):
        amt = (total_amount * m['pct'] / 100).quantize(Decimal('0.01'))
        due = m.get('date') or (booking.booking_date + timedelta(days=m['days_offset']))
        result.append(PaymentMilestone(
            tenant_id=booking.tenant_id,
            booking=booking,
            milestone_name=m['name'],
            due_date=due,
            amount=amt,
            percentage=m['pct'],
            order_index=i,
        ))
    return result


def _generate_construction_linked_milestones(booking, total_amount):
    """
    Construction Linked Plan — standard 10 stages.
    """
    stages = [
        ('Token Amount', Decimal('5'), 0),
        ('Agreement Amount', Decimal('5'), 30),
        ('On Foundation / Excavation', Decimal('10'), 90),
        ('On Plinth Level', Decimal('10'), 180),
        ('On 2nd Floor Slab', Decimal('10'), 270),
        ('On 4th Floor Slab', Decimal('10'), 360),
        ('On 6th Floor Slab', Decimal('10'), 450),
        ('On Top Floor Slab', Decimal('10'), 540),
        ('On Plastering / Finishing', Decimal('10'), 630),
        ('On Possession', Decimal('20'), 720),
    ]
    result = []
    for i, (name, pct, days) in enumerate(stages):
        amt = (total_amount * pct / 100).quantize(Decimal('0.01'))
        result.append(PaymentMilestone(
            tenant_id=booking.tenant_id,
            booking=booking,
            milestone_name=name,
            due_date=booking.booking_date + timedelta(days=days),
            amount=amt,
            percentage=pct,
            order_index=i,
        ))
    return result


def _generate_milestones(booking, total_amount, plan_type, custom_milestones_data=None):
    if plan_type == PaymentPlanTypeEnum.PLAN_20_80:
        return _generate_20_80_milestones(booking, total_amount)
    elif plan_type == PaymentPlanTypeEnum.CONSTRUCTION_LINKED:
        return _generate_construction_linked_milestones(booking, total_amount)
    else:
        # CUSTOM — create from provided data
        result = []
        for i, m in enumerate(custom_milestones_data or []):
            result.append(PaymentMilestone(
                tenant_id=booking.tenant_id,
                booking=booking,
                milestone_name=m['milestone_name'],
                due_date=m['due_date'],
                amount=m['amount'],
                percentage=m.get('percentage'),
                notes=m.get('notes'),
                order_index=m.get('order_index', i),
            ))
        return result


@extend_schema_view(
    list=extend_schema(description='List all bookings for the tenant'),
    retrieve=extend_schema(description='Get booking detail with payment milestones'),
    create=extend_schema(description='Create a booking and auto-generate payment schedule'),
    update=extend_schema(description='Update a booking'),
    partial_update=extend_schema(description='Partially update a booking'),
    destroy=extend_schema(description='Cancel/delete a booking'),
)
class BookingViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for Bookings.

    Special actions:
    - GET  /{id}/milestones/                — list payment milestones
    - POST /{id}/milestones/{mid}/mark-paid/ — record a payment received
    - GET  /summary/                         — revenue summary (total booked, collected, pending)
    """
    queryset = Booking.objects.select_related(
        'lead', 'unit', 'unit__tower', 'unit__tower__project'
    ).prefetch_related('milestones').all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'bookings'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'status': ['exact', 'in'],
        'payment_plan_type': ['exact'],
        'booking_date': ['gte', 'lte', 'exact'],
        'lead': ['exact'],
        'unit': ['exact'],
    }
    search_fields = ['lead__name', 'lead__phone', 'unit__unit_number']
    ordering_fields = ['booking_date', 'total_amount', 'created_at']
    ordering = ['-booking_date']

    def get_serializer_class(self):
        if self.action == 'list':
            return BookingListSerializer
        if self.action == 'create':
            return BookingCreateSerializer
        return BookingSerializer

    @transaction.atomic
    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        validated = serializer.validated_data
        plan_type = validated.get('payment_plan_type', PaymentPlanTypeEnum.CUSTOM)
        custom_milestones_data = validated.pop('milestones', [])

        booking = serializer.save(
            tenant_id=tenant_id,
            owner_user_id=self.request.user_id,
        )

        # Mark unit as BOOKED and link it
        unit = booking.unit
        unit.status = UnitStatusEnum.BOOKED
        unit.reserved_for_lead_id = booking.lead_id
        unit.save(update_fields=['status', 'reserved_for_lead_id', 'updated_at'])

        # Auto-generate payment milestones
        milestones = _generate_milestones(
            booking, booking.total_amount, plan_type, custom_milestones_data
        )
        if milestones:
            PaymentMilestone.objects.bulk_create(milestones)

        # Auto-create commission if lead came via a broker
        _auto_create_commission(booking, tenant_id)

        logger.info(
            f"Booking #{booking.id} created for lead {booking.lead_id}, "
            f"unit {booking.unit_id}, plan={plan_type}"
        )

    @extend_schema(description='List payment milestones for a booking')
    @action(detail=True, methods=['get'], url_path='milestones')
    def milestones(self, request, pk=None):
        booking = self.get_object()
        qs = booking.milestones.all()
        return Response(PaymentMilestoneSerializer(qs, many=True).data)

    @extend_schema(
        description='Mark a payment milestone as paid (record received amount)',
        request=MilestoneMarkPaidSerializer,
    )
    @action(detail=True, methods=['post'], url_path=r'milestones/(?P<milestone_id>\d+)/mark-paid')
    def mark_milestone_paid(self, request, pk=None, milestone_id=None):
        booking = self.get_object()
        try:
            milestone = booking.milestones.get(id=milestone_id)
        except PaymentMilestone.DoesNotExist:
            return Response({'error': 'Milestone not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = MilestoneMarkPaidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        milestone.received_amount = d['received_amount']
        milestone.received_date = d['received_date']
        milestone.reference_no = d.get('reference_no', '')
        milestone.notes = d.get('notes', milestone.notes)
        milestone.status = (
            MilestoneStatusEnum.PAID
            if d['received_amount'] >= milestone.amount
            else MilestoneStatusEnum.PARTIALLY_PAID
        )
        milestone.save()

        return Response(PaymentMilestoneSerializer(milestone).data)

    @extend_schema(description='Revenue summary: total bookings value, collected, pending')
    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        tenant_id = request.tenant_id
        qs = Booking.objects.filter(
            tenant_id=tenant_id
        ).exclude(status=BookingStatusEnum.CANCELLED)

        project_id = request.query_params.get('project_id')
        if project_id:
            qs = qs.filter(unit__tower__project_id=project_id)

        total_bookings = qs.count()
        total_value = qs.aggregate(v=Sum('total_amount'))['v'] or 0

        milestone_qs = PaymentMilestone.objects.filter(
            tenant_id=tenant_id,
            booking__in=qs,
        )
        collected = milestone_qs.filter(
            status__in=[MilestoneStatusEnum.PAID, MilestoneStatusEnum.PARTIALLY_PAID]
        ).aggregate(s=Sum('received_amount'))['s'] or 0
        pending = milestone_qs.filter(
            status__in=[MilestoneStatusEnum.PENDING, MilestoneStatusEnum.OVERDUE,
                        MilestoneStatusEnum.PARTIALLY_PAID]
        ).aggregate(s=Sum('amount'))['s'] or 0
        overdue = milestone_qs.filter(
            status=MilestoneStatusEnum.OVERDUE
        ).aggregate(s=Sum('amount'))['s'] or 0

        return Response({
            'total_bookings': total_bookings,
            'total_value': total_value,
            'collected': collected,
            'pending': pending,
            'overdue': overdue,
        })

    @extend_schema(description='Get upcoming payment milestones (next 30 days) across all bookings')
    @action(detail=False, methods=['get'], url_path='upcoming-payments')
    def upcoming_payments(self, request):
        from django.utils import timezone
        import datetime
        tenant_id = request.tenant_id
        today = timezone.now().date()
        cutoff = today + datetime.timedelta(days=30)

        milestones = PaymentMilestone.objects.filter(
            tenant_id=tenant_id,
            status__in=[MilestoneStatusEnum.PENDING, MilestoneStatusEnum.PARTIALLY_PAID],
            due_date__gte=today,
            due_date__lte=cutoff,
        ).select_related('booking', 'booking__lead', 'booking__unit').order_by('due_date')

        data = []
        for m in milestones:
            data.append({
                'milestone_id': m.id,
                'booking_id': m.booking_id,
                'lead_name': m.booking.lead.name,
                'lead_phone': m.booking.lead.phone,
                'unit_number': m.booking.unit.unit_number,
                'milestone_name': m.milestone_name,
                'due_date': m.due_date,
                'amount': m.amount,
                'received_amount': m.received_amount,
                'status': m.status,
                'days_until_due': (m.due_date - today).days,
            })
        return Response({'count': len(data), 'results': data})

    @extend_schema(description=(
        'Returns structured data for generating a Demand Letter PDF (use jspdf on frontend). '
        'Contains builder info, buyer details, unit specs, booking amount, and payment schedule.'
    ))
    @action(detail=True, methods=['get'], url_path='demand-letter-data')
    def demand_letter_data(self, request, pk=None):
        booking = self.get_object()
        project = booking.unit.tower.project
        milestones = list(booking.milestones.order_by('order_index', 'due_date').values(
            'id', 'milestone_name', 'due_date', 'amount', 'percentage', 'status'
        ))
        return Response({
            'document_type': 'DEMAND_LETTER',
            'generated_at': __import__('django.utils.timezone', fromlist=['timezone']).timezone.now().isoformat(),
            'builder': _get_builder_info(booking.tenant_id),
            'booking': {
                'id': booking.id,
                'booking_date': booking.booking_date,
                'status': booking.status,
                'total_amount': booking.total_amount,
                'token_amount': booking.token_amount,
                'payment_plan_type': booking.payment_plan_type,
                'agreement_date': booking.agreement_date,
                'registration_date': booking.registration_date,
                'remarks': booking.remarks,
            },
            'buyer': {
                'name': booking.lead.name,
                'phone': booking.lead.phone,
                'email': booking.lead.email,
                'address': booking.lead.address_line1,
                'city': booking.lead.city,
                'state': booking.lead.state,
            },
            'unit': {
                'unit_number': booking.unit.unit_number,
                'floor_number': booking.unit.floor_number,
                'bhk_type': booking.unit.bhk_type,
                'carpet_area': booking.unit.carpet_area,
                'facing': booking.unit.facing,
                'base_price': booking.unit.base_price,
                'total_price': booking.unit.total_price,
            },
            'tower': {
                'name': booking.unit.tower.name,
            },
            'project': {
                'name': project.name,
                'rera_number': project.rera_number,
                'location': project.location,
                'address': project.address,
                'city': project.city,
                'state': project.state,
                'possession_date': project.possession_date,
            },
            'payment_schedule': milestones,
        })

    @extend_schema(description=(
        'Returns structured data for generating a Payment Receipt PDF (use jspdf on frontend). '
        'Call after marking a milestone as paid.'
    ))
    @action(detail=True, methods=['get'], url_path=r'milestones/(?P<milestone_id>\d+)/receipt-data')
    def receipt_data(self, request, pk=None, milestone_id=None):
        booking = self.get_object()
        try:
            milestone = booking.milestones.get(id=milestone_id)
        except PaymentMilestone.DoesNotExist:
            return Response({'error': 'Milestone not found'}, status=status.HTTP_404_NOT_FOUND)

        from django.utils import timezone
        return Response({
            'document_type': 'PAYMENT_RECEIPT',
            'generated_at': timezone.now().isoformat(),
            'receipt_number': f'RCP-{booking.id}-{milestone.id}',
            'booking_id': booking.id,
            'builder': _get_builder_info(booking.tenant_id),
            'buyer': {
                'name': booking.lead.name,
                'phone': booking.lead.phone,
                'email': booking.lead.email,
            },
            'unit': {
                'unit_number': booking.unit.unit_number,
                'floor_number': booking.unit.floor_number,
                'bhk_type': booking.unit.bhk_type,
                'tower': booking.unit.tower.name,
                'project': booking.unit.tower.project.name,
                'rera_number': booking.unit.tower.project.rera_number,
            },
            'payment': {
                'milestone_id': milestone.id,
                'milestone_name': milestone.milestone_name,
                'scheduled_amount': milestone.amount,
                'received_amount': milestone.received_amount,
                'received_date': milestone.received_date,
                'reference_no': milestone.reference_no,
                'status': milestone.status,
                'notes': milestone.notes,
            },
            'booking_summary': {
                'total_amount': booking.total_amount,
                'payment_plan_type': booking.payment_plan_type,
            },
        })
