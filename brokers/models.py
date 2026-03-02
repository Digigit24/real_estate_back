from django.db import models


class BrokerStatusEnum(models.TextChoices):
    PENDING = 'PENDING', 'Pending Approval'
    ACTIVE = 'ACTIVE', 'Active'
    INACTIVE = 'INACTIVE', 'Inactive'
    REJECTED = 'REJECTED', 'Rejected'


class CommissionStatusEnum(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    PAID = 'PAID', 'Paid'
    CANCELLED = 'CANCELLED', 'Cancelled'


class Broker(models.Model):
    """Channel partner / real estate broker registered under a builder."""
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.UUIDField(db_index=True)

    name = models.TextField()
    email = models.TextField(null=True, blank=True)
    phone = models.TextField()
    company_name = models.TextField(null=True, blank=True)
    rera_number = models.TextField(null=True, blank=True)

    # Default commission rate (%) applied when creating a booking via this broker
    commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=2,
        help_text='Default commission rate in %'
    )
    status = models.CharField(
        max_length=20,
        choices=BrokerStatusEnum.choices,
        default=BrokerStatusEnum.ACTIVE,
        db_index=True
    )
    address = models.TextField(null=True, blank=True)
    city = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    owner_user_id = models.UUIDField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'brokers'
        indexes = [
            models.Index(fields=['tenant_id'], name='idx_brokers_tenant_id'),
            models.Index(fields=['status'], name='idx_brokers_status'),
            models.Index(fields=['phone'], name='idx_brokers_phone'),
            models.Index(fields=['owner_user_id'], name='idx_brokers_owner_user_id'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['tenant_id', 'phone'],
                name='unique_broker_phone_per_tenant'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Commission(models.Model):
    """Commission earned by a broker on a booking."""
    id = models.BigAutoField(primary_key=True)
    tenant_id = models.UUIDField(db_index=True)

    broker = models.ForeignKey(
        Broker,
        on_delete=models.PROTECT,
        related_name='commissions',
        db_column='broker_id'
    )
    booking = models.ForeignKey(
        'bookings.Booking',
        on_delete=models.PROTECT,
        related_name='commissions',
        db_column='booking_id'
    )
    lead_id = models.BigIntegerField(db_index=True)

    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=14, decimal_places=2)

    status = models.CharField(
        max_length=20,
        choices=CommissionStatusEnum.choices,
        default=CommissionStatusEnum.PENDING,
        db_index=True
    )
    paid_date = models.DateField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    owner_user_id = models.UUIDField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'commissions'
        indexes = [
            models.Index(fields=['tenant_id'], name='idx_commissions_tenant_id'),
            models.Index(fields=['broker'], name='idx_commissions_broker_id'),
            models.Index(fields=['booking'], name='idx_commissions_booking_id'),
            models.Index(fields=['status'], name='idx_commissions_status'),
            models.Index(fields=['owner_user_id'], name='idx_commissions_owner_user_id'),
        ]

    def __str__(self):
        return f"Commission #{self.id} - Broker: {self.broker.name} - Booking #{self.booking_id}"
