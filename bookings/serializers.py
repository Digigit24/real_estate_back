from rest_framework import serializers
from common.mixins import TenantMixin
from .models import Booking, PaymentMilestone, BookingStatusEnum, MilestoneStatusEnum


class PaymentMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMilestone
        fields = [
            'id', 'booking', 'milestone_name', 'due_date', 'amount',
            'percentage', 'status', 'received_amount', 'received_date',
            'reference_no', 'notes', 'order_index', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentMilestoneCreateSerializer(serializers.ModelSerializer):
    """Used when creating milestones manually (custom plan)."""
    class Meta:
        model = PaymentMilestone
        fields = [
            'milestone_name', 'due_date', 'amount', 'percentage',
            'notes', 'order_index',
        ]


class MilestoneMarkPaidSerializer(serializers.Serializer):
    received_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    received_date = serializers.DateField()
    reference_no = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class BookingSerializer(TenantMixin):
    milestones = PaymentMilestoneSerializer(many=True, read_only=True)
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    lead_phone = serializers.CharField(source='lead.phone', read_only=True)
    unit_number = serializers.CharField(source='unit.unit_number', read_only=True)
    tower_name = serializers.CharField(source='unit.tower.name', read_only=True)
    project_name = serializers.CharField(source='unit.tower.project.name', read_only=True)
    project_id = serializers.IntegerField(source='unit.tower.project.id', read_only=True)
    total_collected = serializers.SerializerMethodField()
    total_pending = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'lead', 'lead_name', 'lead_phone',
            'unit', 'unit_number', 'tower_name', 'project_name', 'project_id',
            'booking_date', 'token_amount', 'total_amount', 'payment_plan_type',
            'status', 'agreement_date', 'registration_date',
            'cancellation_date', 'cancellation_reason', 'remarks',
            'owner_user_id', 'created_at', 'updated_at',
            'milestones', 'total_collected', 'total_pending',
        ]
        read_only_fields = [
            'id', 'lead_name', 'lead_phone', 'unit_number', 'tower_name',
            'project_name', 'project_id', 'milestones', 'owner_user_id',
            'total_collected', 'total_pending', 'created_at', 'updated_at',
        ]

    def get_total_collected(self, obj):
        total = sum(
            m.received_amount or 0
            for m in obj.milestones.all()
            if m.status in (MilestoneStatusEnum.PAID, MilestoneStatusEnum.PARTIALLY_PAID)
        )
        return total

    def get_total_pending(self, obj):
        total = sum(
            m.amount - (m.received_amount or 0)
            for m in obj.milestones.all()
            if m.status in (MilestoneStatusEnum.PENDING, MilestoneStatusEnum.PARTIALLY_PAID, MilestoneStatusEnum.OVERDUE)
        )
        return total


class BookingListSerializer(TenantMixin):
    lead_name = serializers.CharField(source='lead.name', read_only=True)
    lead_phone = serializers.CharField(source='lead.phone', read_only=True)
    unit_number = serializers.CharField(source='unit.unit_number', read_only=True)
    tower_name = serializers.CharField(source='unit.tower.name', read_only=True)
    project_name = serializers.CharField(source='unit.tower.project.name', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'lead', 'lead_name', 'lead_phone',
            'unit', 'unit_number', 'tower_name', 'project_name',
            'booking_date', 'token_amount', 'total_amount',
            'payment_plan_type', 'status', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class BookingCreateSerializer(TenantMixin):
    """
    Serializer for creating a booking.
    Accepts optional milestones list (for CUSTOM plan).
    For 20_80 and CONSTRUCTION_LINKED plans, milestones are auto-generated.
    """
    milestones = PaymentMilestoneCreateSerializer(many=True, required=False)

    class Meta:
        model = Booking
        fields = [
            'lead', 'unit', 'booking_date', 'token_amount', 'total_amount',
            'payment_plan_type', 'status', 'agreement_date', 'registration_date',
            'remarks', 'milestones',
        ]

    def validate(self, attrs):
        unit = attrs.get('unit')
        if unit and unit.status not in ('AVAILABLE', 'RESERVED'):
            raise serializers.ValidationError(
                {'unit': f'Unit is not available for booking. Current status: {unit.status}'}
            )
        plan = attrs.get('payment_plan_type', 'CUSTOM')
        if plan == 'CUSTOM' and not attrs.get('milestones'):
            raise serializers.ValidationError(
                {'milestones': 'At least one milestone is required for CUSTOM payment plan.'}
            )
        return attrs
