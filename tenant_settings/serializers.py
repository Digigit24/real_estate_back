from rest_framework import serializers
from .models import TenantSettings, PaymentPlanTemplate


class TenantSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantSettings
        fields = [
            'tenant_id', 'company_name', 'tagline', 'logo_url', 'favicon_url',
            'primary_color', 'secondary_color', 'accent_color',
            'subdomain', 'custom_domain',
            'support_email', 'support_phone',
            'address', 'city', 'state', 'pincode', 'gstin',
            'pdf_header_text', 'pdf_footer_text', 'signature_url',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['tenant_id', 'created_at', 'updated_at']


class PaymentPlanTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentPlanTemplate
        fields = [
            'id', 'name', 'description', 'plan_type', 'stages',
            'is_active', 'is_default', 'owner_user_id', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'owner_user_id', 'created_at', 'updated_at']

    def validate_stages(self, stages):
        if not isinstance(stages, list) or len(stages) == 0:
            raise serializers.ValidationError('stages must be a non-empty list.')
        total_pct = sum(s.get('percentage', 0) for s in stages)
        if abs(total_pct - 100) > 0.01:
            raise serializers.ValidationError(
                f'Stage percentages must sum to 100. Current sum: {total_pct}'
            )
        for s in stages:
            if 'name' not in s or 'percentage' not in s or 'days_from_booking' not in s:
                raise serializers.ValidationError(
                    'Each stage must have: name, percentage, days_from_booking'
                )
        return stages


class PaymentPlanPreviewSerializer(serializers.Serializer):
    """Request body for previewing payment plan milestones."""
    template_id = serializers.IntegerField(help_text='ID of the PaymentPlanTemplate to preview')
    booking_date = serializers.DateField(help_text='Booking date used to calculate milestone due dates (YYYY-MM-DD)')
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2, help_text='Total booking amount in INR')


class PaymentPlanMilestoneSerializer(serializers.Serializer):
    """A single computed milestone in the preview response."""
    order_index = serializers.IntegerField()
    milestone_name = serializers.CharField()
    percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    due_date = serializers.DateField()


class PaymentPlanPreviewResponseSerializer(serializers.Serializer):
    """Response body from the payment plan preview action."""
    template_id = serializers.IntegerField()
    template_name = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    milestones = PaymentPlanMilestoneSerializer(many=True)
