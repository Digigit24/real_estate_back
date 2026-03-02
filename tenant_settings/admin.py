from django.contrib import admin
from .models import TenantSettings, PaymentPlanTemplate


@admin.register(TenantSettings)
class TenantSettingsAdmin(admin.ModelAdmin):
    list_display = ['tenant_id', 'company_name', 'subdomain', 'primary_color', 'updated_at']
    search_fields = ['company_name', 'subdomain']
    readonly_fields = ['tenant_id', 'created_at', 'updated_at']


@admin.register(PaymentPlanTemplate)
class PaymentPlanTemplateAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'plan_type', 'is_active', 'is_default', 'tenant_id', 'created_at']
    list_filter = ['plan_type', 'is_active', 'is_default']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
