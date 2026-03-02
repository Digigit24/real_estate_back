"""
Management command to seed real estate pipeline stages for a tenant.

Usage:
    python manage.py seed_re_pipeline --tenant_id <uuid>
    python manage.py seed_re_pipeline --tenant_id <uuid> --force  # overwrites existing
"""
from django.core.management.base import BaseCommand, CommandError
from crm.models import LeadStatus


RE_PIPELINE_STAGES = [
    {"name": "Inquiry",                "order_index": 1,  "color_hex": "#94A3B8", "is_won": False, "is_lost": False},
    {"name": "Qualified",              "order_index": 2,  "color_hex": "#60A5FA", "is_won": False, "is_lost": False},
    {"name": "Site Visit Scheduled",   "order_index": 3,  "color_hex": "#FBBF24", "is_won": False, "is_lost": False},
    {"name": "Site Visit Done",        "order_index": 4,  "color_hex": "#F97316", "is_won": False, "is_lost": False},
    {"name": "Shortlisted Unit",       "order_index": 5,  "color_hex": "#A78BFA", "is_won": False, "is_lost": False},
    {"name": "Negotiation",            "order_index": 6,  "color_hex": "#EC4899", "is_won": False, "is_lost": False},
    {"name": "Token Paid",             "order_index": 7,  "color_hex": "#10B981", "is_won": False, "is_lost": False},
    {"name": "Agreement",              "order_index": 8,  "color_hex": "#059669", "is_won": False, "is_lost": False},
    {"name": "Registered",             "order_index": 9,  "color_hex": "#047857", "is_won": False, "is_lost": False},
    {"name": "Closed / Won",           "order_index": 10, "color_hex": "#16A34A", "is_won": True,  "is_lost": False},
    {"name": "Lost",                   "order_index": 11, "color_hex": "#EF4444", "is_won": False, "is_lost": True},
    {"name": "Not Interested",         "order_index": 12, "color_hex": "#6B7280", "is_won": False, "is_lost": True},
]


class Command(BaseCommand):
    help = 'Seed real estate pipeline stages (LeadStatus) for a tenant'

    def add_arguments(self, parser):
        parser.add_argument('--tenant_id', required=True, help='Tenant UUID')
        parser.add_argument(
            '--force',
            action='store_true',
            help='Delete existing stages for tenant and re-create'
        )

    def handle(self, *args, **options):
        tenant_id = options['tenant_id']
        force = options['force']

        existing_count = LeadStatus.objects.filter(tenant_id=tenant_id).count()

        if existing_count > 0 and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'Tenant {tenant_id} already has {existing_count} pipeline stage(s). '
                    f'Use --force to overwrite.'
                )
            )
            return

        if force and existing_count > 0:
            LeadStatus.objects.filter(tenant_id=tenant_id).delete()
            self.stdout.write(f'Deleted {existing_count} existing stage(s) for tenant {tenant_id}')

        stages = [
            LeadStatus(tenant_id=tenant_id, **stage)
            for stage in RE_PIPELINE_STAGES
        ]
        LeadStatus.objects.bulk_create(stages)

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {len(stages)} RE pipeline stages for tenant {tenant_id}'
            )
        )
