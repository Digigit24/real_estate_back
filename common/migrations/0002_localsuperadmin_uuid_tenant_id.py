import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Convert LocalSuperAdmin.tenant_id from IntegerField to UUIDField.

    This table is only used in development, so existing rows are cleared
    before the column type is changed (avoids complex PostgreSQL casting).
    Re-create your local super admin with:
        python manage.py create_local_superadmin --email <email> --password <pass>
    """

    dependencies = [
        ('common', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
                        DELETE FROM common_local_super_admin;
                        ALTER TABLE common_local_super_admin DROP COLUMN tenant_id;
                        ALTER TABLE common_local_super_admin
                            ADD COLUMN tenant_id uuid NOT NULL
                            DEFAULT '00000000-0000-0000-0000-000000000000';
                        ALTER TABLE common_local_super_admin
                            ALTER COLUMN tenant_id DROP DEFAULT;
                    """,
                    reverse_sql="""
                        DELETE FROM common_local_super_admin;
                        ALTER TABLE common_local_super_admin DROP COLUMN tenant_id;
                        ALTER TABLE common_local_super_admin
                            ADD COLUMN tenant_id integer NOT NULL DEFAULT 1;
                        ALTER TABLE common_local_super_admin
                            ALTER COLUMN tenant_id DROP DEFAULT;
                    """,
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name='localsuperadmin',
                    name='tenant_id',
                    field=models.UUIDField(default=uuid.uuid4),
                ),
            ],
        ),
    ]
