import uuid
from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class LocalSuperAdmin(models.Model):
    """
    Local super admin credentials for development/standalone use.
    Used when the external SuperAdmin service is unavailable.
    """
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    tenant_id = models.UUIDField(default=uuid.uuid4)
    tenant_slug = models.CharField(max_length=100, default='default')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'common_local_super_admin'
        verbose_name = 'Local Super Admin'
        verbose_name_plural = 'Local Super Admins'

    def __str__(self):
        return self.email

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)
