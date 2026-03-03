import uuid
from django.db import migrations, models


def migrate_tenant_id_to_uuid(apps, schema_editor):
    LocalSuperAdmin = apps.get_model('common', 'LocalSuperAdmin')
    namespace = uuid.UUID('11111111-1111-1111-1111-111111111111')

    for admin in LocalSuperAdmin.objects.all():
        old_value = getattr(admin, 'tenant_id', None)
        if old_value is None or str(old_value).strip() == '':
            new_uuid = uuid.uuid4()
        else:
            try:
                new_uuid = uuid.UUID(str(old_value))
            except (ValueError, TypeError):
                new_uuid = uuid.uuid5(namespace, f'legacy-tenant-{old_value}')

        admin.tenant_uuid = new_uuid
        admin.save(update_fields=['tenant_uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='localsuperadmin',
            name='tenant_uuid',
            field=models.UUIDField(null=True),
        ),
        migrations.RunPython(migrate_tenant_id_to_uuid, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='localsuperadmin',
            name='tenant_id',
        ),
        migrations.RenameField(
            model_name='localsuperadmin',
            old_name='tenant_uuid',
            new_name='tenant_id',
        ),
        migrations.AlterField(
            model_name='localsuperadmin',
            name='tenant_id',
            field=models.UUIDField(default=uuid.uuid4),
        ),
    ]
