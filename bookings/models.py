from django.db import models
from crm.models import Lead
from inventory.models import Unit


class PaymentPlanTypeEnum(models.TextChoices):
    PLAN_20_80 = '20_80', '20:80 Plan'
    CONSTRUCTION_LINKED = 'CONSTRUCTION_LINKED', 'Construction Linked Plan'
    CUSTOM = 'CUSTOM', 'Custom Plan'


class BookingStatusEnum(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    TOKEN_PAID = 'TOKEN_PAID', 'Token Paid'
    AGREEMENT_DONE = 'AGREEMENT_DONE', 'Agreement Done'
    REGISTERED = 'REGISTERED', 'Registered'
    CANCELLED = 'CANCELLED', 'Cancelled'


class MilestoneStatusEnum(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PAID = 'PAID', 'Paid'
    PARTIALLY_PAID = 'PARTIALLY_PAID', 'Partially Paid'
    OVERDUE = 'OVERDUE', 'Overdue'
    WAIVED = 'WAIVED', 'Waived'


class Booking(models.Model):
    """Formal booking of a unit by a buyer (lead)."""
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.UUIDField(db_index=True)

    lead = models.ForeignKey(
        Lead,
        on_delete=models.PROTECT,
        related_name='bookings',
        db_column='lead_id'
    )
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name='bookings',
        db_column='unit_id'
    )

    booking_date = models.DateField()
    token_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_plan_type = models.CharField(
        max_length=30,
        choices=PaymentPlanTypeEnum.choices,
        default=PaymentPlanTypeEnum.CUSTOM
    )
    status = models.CharField(
        max_length=20,
        choices=BookingStatusEnum.choices,
        default=BookingStatusEnum.DRAFT,
        db_index=True
    )

    agreement_date = models.DateField(null=True, blank=True)
    registration_date = models.DateField(null=True, blank=True)
    cancellation_date = models.DateField(null=True, blank=True)
    cancellation_reason = models.TextField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    owner_user_id = models.UUIDField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'bookings'
        indexes = [
            models.Index(fields=['tenant_id'], name='idx_bookings_tenant_id'),
            models.Index(fields=['lead'], name='idx_bookings_lead_id'),
            models.Index(fields=['unit'], name='idx_bookings_unit_id'),
            models.Index(fields=['status'], name='idx_bookings_status'),
            models.Index(fields=['booking_date'], name='idx_bookings_date'),
            models.Index(fields=['owner_user_id'], name='idx_bookings_owner_user_id'),
        ]

    def __str__(self):
        return f"Booking #{self.id} - {self.lead.name} - Unit {self.unit.unit_number}"


class PaymentMilestone(models.Model):
    """A single payment installment in a booking's payment schedule."""
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.UUIDField(db_index=True)

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='milestones',
        db_column='booking_id'
    )
    milestone_name = models.TextField()
    due_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text='Percentage of total amount this milestone represents'
    )
    status = models.CharField(
        max_length=20,
        choices=MilestoneStatusEnum.choices,
        default=MilestoneStatusEnum.PENDING,
        db_index=True
    )
    received_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    reference_no = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    order_index = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_milestones'
        ordering = ['order_index', 'due_date']
        indexes = [
            models.Index(fields=['tenant_id'], name='idx_milestones_tenant_id'),
            models.Index(fields=['booking'], name='idx_milestones_booking_id'),
            models.Index(fields=['status'], name='idx_milestones_status'),
            models.Index(fields=['due_date'], name='idx_milestones_due_date'),
        ]

    def __str__(self):
        return f"Booking #{self.booking_id} - {self.milestone_name} - {self.due_date}"
