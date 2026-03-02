from rest_framework import serializers
from common.mixins import TenantMixin
from .models import Broker, Commission, CommissionStatusEnum


class BrokerSerializer(TenantMixin):
    leads_count = serializers.SerializerMethodField()
    bookings_count = serializers.SerializerMethodField()
    total_commission_earned = serializers.SerializerMethodField()

    class Meta:
        model = Broker
        fields = [
            'id', 'name', 'email', 'phone', 'company_name', 'rera_number',
            'commission_rate', 'status', 'address', 'city', 'notes',
            'owner_user_id', 'created_at', 'updated_at',
            'leads_count', 'bookings_count', 'total_commission_earned',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            'leads_count', 'bookings_count', 'total_commission_earned',
        ]

    def get_leads_count(self, obj):
        from crm.models import Lead
        return Lead.objects.filter(tenant_id=obj.tenant_id, broker_id=obj.id).count()

    def get_bookings_count(self, obj):
        return obj.commissions.count()

    def get_total_commission_earned(self, obj):
        from django.db.models import Sum
        result = obj.commissions.filter(
            status__in=[CommissionStatusEnum.PENDING, CommissionStatusEnum.PAID]
        ).aggregate(total=Sum('commission_amount'))
        return result['total'] or 0


class BrokerListSerializer(TenantMixin):
    class Meta:
        model = Broker
        fields = [
            'id', 'name', 'phone', 'company_name', 'commission_rate',
            'status', 'city', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class CommissionSerializer(TenantMixin):
    broker_name = serializers.CharField(source='broker.name', read_only=True)
    broker_phone = serializers.CharField(source='broker.phone', read_only=True)
    booking_date = serializers.DateField(source='booking.booking_date', read_only=True)
    unit_number = serializers.CharField(source='booking.unit.unit_number', read_only=True)
    project_name = serializers.CharField(source='booking.unit.tower.project.name', read_only=True)

    class Meta:
        model = Commission
        fields = [
            'id', 'broker', 'broker_name', 'broker_phone',
            'booking', 'booking_date', 'unit_number', 'project_name',
            'lead_id', 'commission_rate', 'commission_amount',
            'status', 'paid_date', 'notes',
            'owner_user_id', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'broker_name', 'broker_phone',
            'booking_date', 'unit_number', 'project_name',
            'created_at', 'updated_at',
        ]


class CommissionCreateSerializer(TenantMixin):
    class Meta:
        model = Commission
        fields = [
            'broker', 'booking', 'lead_id',
            'commission_rate', 'commission_amount',
            'notes',
        ]

    def validate(self, attrs):
        booking = attrs.get('booking')
        broker = attrs.get('broker')
        if booking and broker:
            if booking.tenant_id != broker.tenant_id:
                raise serializers.ValidationError('Broker and Booking must belong to the same tenant.')
        return attrs


class CommissionMarkPaidSerializer(serializers.Serializer):
    paid_date = serializers.DateField()
    notes = serializers.CharField(required=False, allow_blank=True)
