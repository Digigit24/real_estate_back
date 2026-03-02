from rest_framework import serializers
from .models import Payment
from common.mixins import TenantMixin


class PaymentSerializer(TenantMixin):
    """Serializer for Payment model"""
    lead_name = serializers.CharField(source='lead.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'lead', 'lead_name', 'type', 'amount', 'currency',
            'method', 'reference_no', 'notes', 'date', 'due_date', 'status',
            'attachment_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentListSerializer(TenantMixin):
    """Lightweight serializer for listing payments"""
    lead_name = serializers.CharField(source='lead.name', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'lead', 'lead_name', 'type', 'amount', 'currency',
            'date', 'due_date', 'status', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PaymentHistorySerializer(serializers.ModelSerializer):
    """Serializer for the payment history table view"""
    total = serializers.DecimalField(source='amount', max_digits=12, decimal_places=2)

    class Meta:
        model = Payment
        fields = ['id', 'date', 'due_date', 'total', 'currency', 'status']
        read_only_fields = ['id', 'date', 'due_date', 'total', 'currency', 'status']
