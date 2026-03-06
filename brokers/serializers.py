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
            'id', 'owner_user_id', 'created_at', 'updated_at',
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
    lead_name = serializers.SerializerMethodField()

    class Meta:
        model = Commission
        fields = [
            'id', 'broker', 'broker_name', 'broker_phone',
            'booking', 'booking_date', 'unit_number', 'project_name',
            'lead_id', 'lead_name', 'commission_rate', 'commission_amount',
            'status', 'paid_date', 'notes',
            'owner_user_id', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'broker_name', 'broker_phone',
            'booking_date', 'unit_number', 'project_name',
            'lead_name', 'owner_user_id', 'created_at', 'updated_at',
        ]

    def get_lead_name(self, obj):
        if not obj.lead_id:
            return None
        from crm.models import Lead
        try:
            return Lead.objects.get(id=obj.lead_id).name
        except Lead.DoesNotExist:
            return None


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


class BrokerRegisterSerializer(serializers.Serializer):
    """Request body for broker self-registration."""
    tenant_id = serializers.UUIDField(help_text='UUID of the builder tenant this broker is registering under')
    name = serializers.CharField(max_length=255, help_text='Full name of the broker')
    phone = serializers.CharField(max_length=20, help_text='Phone number (used as login credential)')
    password = serializers.CharField(write_only=True, help_text='Password for broker portal login')
    email = serializers.EmailField(required=False, allow_blank=True, help_text='Optional email address')
    company_name = serializers.CharField(required=False, allow_blank=True, max_length=255, help_text='Brokerage firm name')
    rera_number = serializers.CharField(required=False, allow_blank=True, max_length=100, help_text='RERA registration number')
    city = serializers.CharField(required=False, allow_blank=True, max_length=100, help_text='City of operation')


class BrokerRegisterResponseSerializer(serializers.Serializer):
    """Response body after successful broker self-registration."""
    message = serializers.CharField(help_text='Human-readable confirmation message')
    broker_id = serializers.IntegerField(help_text='ID of the newly created broker record')
    status = serializers.CharField(help_text='Broker status after registration')


class BrokerLoginSerializer(serializers.Serializer):
    """Request body for broker portal login."""
    tenant_id = serializers.UUIDField(help_text='UUID of the builder tenant')
    phone = serializers.CharField(max_length=20, help_text='Phone number (login credential)')
    password = serializers.CharField(write_only=True, help_text='Broker portal password')


class BrokerLoginResponseSerializer(serializers.Serializer):
    """Response body after successful broker login."""
    token = serializers.CharField(help_text='BrokerToken — send as "BrokerToken <token>" header on all subsequent requests')
    broker_id = serializers.IntegerField(help_text='ID of the authenticated broker')
    name = serializers.CharField(help_text='Broker full name')
    phone = serializers.CharField(help_text='Broker phone number')
    company_name = serializers.CharField(allow_null=True, help_text='Brokerage firm name')
    status = serializers.CharField(help_text='Broker account status (ACTIVE)')
    expires_at = serializers.DateTimeField(help_text='Token expiry datetime')


class BrokerSubmitLeadSerializer(serializers.Serializer):
    """Request body for broker submitting a buyer lead."""
    name = serializers.CharField(max_length=255, help_text='Buyer full name (required)')
    phone = serializers.CharField(max_length=20, help_text='Buyer phone number (required)')
    email = serializers.EmailField(required=False, allow_blank=True, help_text='Buyer email (optional)')
    budget_min = serializers.DecimalField(required=False, allow_null=True, max_digits=14, decimal_places=2, help_text='Min budget in INR')
    budget_max = serializers.DecimalField(required=False, allow_null=True, max_digits=14, decimal_places=2, help_text='Max budget in INR')
    bhk_preference = serializers.CharField(required=False, allow_blank=True, max_length=50, help_text='e.g. 2BHK, 3BHK')
    preferred_project_id = serializers.IntegerField(required=False, allow_null=True, help_text='Integer ID of preferred project (optional)')
    notes = serializers.CharField(required=False, allow_blank=True, help_text='Additional notes about the buyer')


class BrokerSubmitLeadResponseSerializer(serializers.Serializer):
    """Response body after broker submits a lead."""
    message = serializers.CharField(help_text='Confirmation message')
    lead_id = serializers.IntegerField(help_text='ID of the newly created lead in CRM')
    lead_name = serializers.CharField(help_text='Buyer name')
    lead_phone = serializers.CharField(help_text='Buyer phone number')
