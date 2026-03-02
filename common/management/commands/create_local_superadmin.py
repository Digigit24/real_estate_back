import getpass
from django.core.management.base import BaseCommand
from common.models import LocalSuperAdmin


class Command(BaseCommand):
    help = 'Create a local super admin account for standalone/development use'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, help='Admin email address')
        parser.add_argument('--password', type=str, help='Admin password')
        parser.add_argument('--first-name', type=str, default='Super', help='First name')
        parser.add_argument('--last-name', type=str, default='Admin', help='Last name')
        parser.add_argument('--tenant-id', type=int, default=1, help='Tenant ID')
        parser.add_argument('--tenant-slug', type=str, default='default', help='Tenant slug')

    def handle(self, *args, **options):
        email = options.get('email')
        password = options.get('password')

        if not email:
            email = input('Email: ').strip()

        if not email:
            self.stderr.write(self.style.ERROR('Email is required.'))
            return

        if not password:
            password = getpass.getpass('Password: ')
            confirm = getpass.getpass('Confirm Password: ')
            if password != confirm:
                self.stderr.write(self.style.ERROR('Passwords do not match.'))
                return

        if not password:
            self.stderr.write(self.style.ERROR('Password is required.'))
            return

        admin, created = LocalSuperAdmin.objects.get_or_create(email=email)
        admin.first_name = options.get('first_name') or 'Super'
        admin.last_name = options.get('last_name') or 'Admin'
        admin.tenant_id = options.get('tenant_id') or 1
        admin.tenant_slug = options.get('tenant_slug') or 'default'
        admin.is_active = True
        admin.set_password(password)
        admin.save()

        action = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'{action} local super admin: {email}'
        ))
        self.stdout.write(f'  Tenant ID:   {admin.tenant_id}')
        self.stdout.write(f'  Tenant Slug: {admin.tenant_slug}')
        self.stdout.write('')
        self.stdout.write('You can now login at: http://localhost:8000/auth/superadmin-login/')
