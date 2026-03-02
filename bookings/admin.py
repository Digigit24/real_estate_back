from django.contrib import admin
from .models import Booking, PaymentMilestone


class PaymentMilestoneInline(admin.TabularInline):
    model = PaymentMilestone
    extra = 0
    fields = ['milestone_name', 'due_date', 'amount', 'percentage', 'status', 'received_amount', 'received_date', 'reference_no']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'lead', 'unit', 'booking_date', 'total_amount', 'payment_plan_type', 'status', 'created_at']
    list_filter = ['status', 'payment_plan_type', 'booking_date']
    search_fields = ['lead__name', 'lead__phone', 'unit__unit_number']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PaymentMilestoneInline]


@admin.register(PaymentMilestone)
class PaymentMilestoneAdmin(admin.ModelAdmin):
    list_display = ['id', 'booking', 'milestone_name', 'due_date', 'amount', 'status', 'received_amount']
    list_filter = ['status', 'due_date']
    search_fields = ['booking__lead__name', 'milestone_name']
    readonly_fields = ['created_at', 'updated_at']
