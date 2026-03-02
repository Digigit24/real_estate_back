from django.db import models


class TenantSettings(models.Model):
    """White-label branding and configuration per tenant (one row per tenant)."""
    tenant_id = models.UUIDField(primary_key=True)

    # Branding
    company_name = models.TextField(null=True, blank=True)
    tagline = models.TextField(null=True, blank=True)
    logo_url = models.TextField(null=True, blank=True)
    favicon_url = models.TextField(null=True, blank=True)
    primary_color = models.CharField(max_length=7, default='#2563EB', help_text='Hex color e.g. #2563EB')
    secondary_color = models.CharField(max_length=7, default='#1E40AF')
    accent_color = models.CharField(max_length=7, default='#10B981')

    # Domain
    subdomain = models.TextField(null=True, blank=True, unique=True, help_text='e.g. sunrise for sunrise.yourapp.com')
    custom_domain = models.TextField(null=True, blank=True, help_text='e.g. crm.sunrisedevelopers.com')

    # Contact
    support_email = models.TextField(null=True, blank=True)
    support_phone = models.TextField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    city = models.TextField(null=True, blank=True)
    state = models.TextField(null=True, blank=True)
    pincode = models.TextField(null=True, blank=True)
    gstin = models.TextField(null=True, blank=True)

    # PDF / Document settings
    pdf_header_text = models.TextField(null=True, blank=True, help_text='Text shown in PDF header')
    pdf_footer_text = models.TextField(null=True, blank=True, help_text='Text shown in PDF footer')
    signature_url = models.TextField(null=True, blank=True, help_text='Authorized signatory signature image URL')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenant_settings'

    def __str__(self):
        return f"Settings for tenant {self.tenant_id}"


class PaymentPlanTemplate(models.Model):
    """
    Reusable configurable payment plan template per tenant.
    The stages JSON defines the installment breakdown.
    """
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.UUIDField(db_index=True)
    name = models.TextField(help_text='e.g. "20:80 Plan", "My Construction Plan"')
    description = models.TextField(null=True, blank=True)
    plan_type = models.CharField(
        max_length=30,
        choices=[
            ('20_80', '20:80 Plan'),
            ('CONSTRUCTION_LINKED', 'Construction Linked'),
            ('CUSTOM', 'Custom'),
        ],
        default='CUSTOM'
    )
    # JSON array: [{"name": "Token", "percentage": 10, "days_from_booking": 0}, ...]
    stages = models.JSONField(
        help_text='Array of {name, percentage, days_from_booking} objects. percentages must sum to 100.'
    )
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text='Use this plan as the default for new bookings')
    owner_user_id = models.UUIDField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_plan_templates'
        indexes = [
            models.Index(fields=['tenant_id'], name='idx_ppt_tenant_id'),
            models.Index(fields=['tenant_id', 'is_active'], name='idx_ppt_tenant_active'),
        ]

    def __str__(self):
        return f"{self.name} (tenant {self.tenant_id})"
