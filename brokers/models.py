import hashlib
import secrets
from django.db import models
from django.utils import timezone


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

    # Portal auth fields
    portal_email = models.TextField(null=True, blank=True, db_index=True, help_text='Login email for broker portal')
    password_hash = models.TextField(null=True, blank=True)

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


class BrokerSession(models.Model):
    """Simple token-based session for the broker portal."""
    id = models.BigAutoField(primary_key=True)
    broker = models.ForeignKey(
        Broker,
        on_delete=models.CASCADE,
        related_name='sessions',
        db_column='broker_id'
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'broker_sessions'
        indexes = [
            models.Index(fields=['token'], name='idx_broker_sessions_token'),
            models.Index(fields=['broker'], name='idx_broker_sessions_broker_id'),
        ]

    def is_valid(self):
        return timezone.now() < self.expires_at

    def __str__(self):
        return f"Session for broker {self.broker_id}"

    @classmethod
    def create_for_broker(cls, broker, days=30):
        token = secrets.token_hex(32)
        expires_at = timezone.now() + timezone.timedelta(days=days)
        return cls.objects.create(broker=broker, token=token, expires_at=expires_at)


# Utility helpers on Broker model (monkey-patched to keep models.py clean)
def _set_password(self, raw_password):
    self.password_hash = hashlib.sha256(raw_password.encode()).hexdigest()

def _check_password(self, raw_password):
    return self.password_hash == hashlib.sha256(raw_password.encode()).hexdigest()

Broker.set_password = _set_password
Broker.check_password = _check_password
