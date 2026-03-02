from django.contrib import admin
from .models import Broker, Commission


class CommissionInline(admin.TabularInline):
    model = Commission
    extra = 0
    fields = ['booking', 'commission_rate', 'commission_amount', 'status', 'paid_date']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Broker)
class BrokerAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'phone', 'company_name', 'commission_rate', 'status', 'city', 'created_at']
    list_filter = ['status', 'city']
    search_fields = ['name', 'phone', 'email', 'company_name', 'rera_number']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [CommissionInline]


@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
    list_display = ['id', 'broker', 'booking', 'commission_rate', 'commission_amount', 'status', 'paid_date']
    list_filter = ['status']
    search_fields = ['broker__name', 'broker__phone']
    readonly_fields = ['created_at', 'updated_at']
