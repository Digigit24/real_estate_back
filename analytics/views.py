"""
Builder Dashboard Analytics API.

Endpoints:
  GET /api/analytics/inventory/          — inventory health per project
  GET /api/analytics/sales-funnel/       — leads at each pipeline stage + conversion rates
  GET /api/analytics/revenue/            — bookings value, collected, pending
  GET /api/analytics/agent-leaderboard/  — agent performance (site visits, bookings, conversion)
  GET /api/analytics/lead-sources/       — lead source ROI (leads, site visits, bookings per source)
  GET /api/analytics/overview/           — single-call summary for the main dashboard
"""

import datetime
from decimal import Decimal

from django.db.models import Count, Sum, Q, F
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.response import Response
from rest_framework.views import APIView

from bookings.models import Booking, PaymentMilestone, BookingStatusEnum, MilestoneStatusEnum
from common.permissions import JWTAuthentication, HasCRMPermission
from crm.models import Lead, LeadActivity, ActivityTypeEnum, LeadSourceEnum
from inventory.models import Project, Unit, UnitStatusEnum


def _get_tenant(request):
    return getattr(request, 'tenant_id', None)


class InventoryHealthView(APIView):
    """
    Inventory health: unit counts by status, broken down by project.
    Query params:
      - project_id: filter to a single project
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'analytics'

    @extend_schema(
        description='Inventory health: unit counts by status per project',
        parameters=[OpenApiParameter('project_id', int, required=False)],
    )
    def get(self, request):
        tenant_id = _get_tenant(request)
        qs = Unit.objects.filter(tenant_id=tenant_id, is_active=True)
        project_id = request.query_params.get('project_id')
        if project_id:
            qs = qs.filter(tower__project_id=project_id)

        # Aggregate counts by project
        projects = Project.objects.filter(tenant_id=tenant_id, is_active=True)
        if project_id:
            projects = projects.filter(id=project_id)

        result = []
        for project in projects:
            project_units = qs.filter(tower__project=project)
            counts = project_units.values('status').annotate(count=Count('id'))
            by_status = {row['status']: row['count'] for row in counts}
            total = sum(by_status.values())
            result.append({
                'project_id': project.id,
                'project_name': project.name,
                'total': total,
                'available': by_status.get(UnitStatusEnum.AVAILABLE, 0),
                'reserved': by_status.get(UnitStatusEnum.RESERVED, 0),
                'booked': by_status.get(UnitStatusEnum.BOOKED, 0),
                'registered': by_status.get(UnitStatusEnum.REGISTERED, 0),
                'sold': by_status.get(UnitStatusEnum.SOLD, 0),
                'blocked': by_status.get(UnitStatusEnum.BLOCKED, 0),
            })

        # Overall totals
        all_counts = qs.values('status').annotate(count=Count('id'))
        overall = {row['status']: row['count'] for row in all_counts}
        grand_total = sum(overall.values())

        return Response({
            'overall': {
                'total': grand_total,
                'available': overall.get(UnitStatusEnum.AVAILABLE, 0),
                'reserved': overall.get(UnitStatusEnum.RESERVED, 0),
                'booked': overall.get(UnitStatusEnum.BOOKED, 0),
                'registered': overall.get(UnitStatusEnum.REGISTERED, 0),
                'sold': overall.get(UnitStatusEnum.SOLD, 0),
                'blocked': overall.get(UnitStatusEnum.BLOCKED, 0),
            },
            'by_project': result,
        })


class SalesFunnelView(APIView):
    """
    Sales funnel: lead count at each pipeline stage + stage conversion rates.
    Query params:
      - days: look at leads created in last N days (default: all time)
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'analytics'

    @extend_schema(
        description='Sales funnel: lead count per pipeline stage with conversion rates',
        parameters=[OpenApiParameter('days', int, required=False)],
    )
    def get(self, request):
        tenant_id = _get_tenant(request)
        qs = Lead.objects.filter(tenant_id=tenant_id)

        days = request.query_params.get('days')
        if days:
            cutoff = timezone.now() - datetime.timedelta(days=int(days))
            qs = qs.filter(created_at__gte=cutoff)

        # Count leads by status (stage)
        stage_counts = qs.filter(
            status__isnull=False
        ).values(
            'status__id', 'status__name', 'status__order_index', 'status__color_hex',
            'status__is_won', 'status__is_lost'
        ).annotate(count=Count('id')).order_by('status__order_index')

        total_leads = qs.count()
        stages = []
        for row in stage_counts:
            stages.append({
                'status_id': row['status__id'],
                'stage_name': row['status__name'],
                'order_index': row['status__order_index'],
                'color_hex': row['status__color_hex'],
                'is_won': row['status__is_won'],
                'is_lost': row['status__is_lost'],
                'count': row['count'],
                'percentage': round(row['count'] / total_leads * 100, 1) if total_leads else 0,
            })

        # Won / Lost counts
        won_count = qs.filter(status__is_won=True).count()
        lost_count = qs.filter(status__is_lost=True).count()
        conversion_rate = round(won_count / total_leads * 100, 1) if total_leads else 0

        # Site visits (activity-based)
        site_visits = LeadActivity.objects.filter(
            tenant_id=tenant_id,
            type=ActivityTypeEnum.SITE_VISIT,
        )
        if days:
            site_visits = site_visits.filter(happened_at__gte=cutoff)
        site_visit_count = site_visits.values('lead').distinct().count()

        return Response({
            'total_leads': total_leads,
            'won': won_count,
            'lost': lost_count,
            'conversion_rate': conversion_rate,
            'site_visits': site_visit_count,
            'stages': stages,
        })


class RevenueView(APIView):
    """
    Revenue summary: bookings value, collected, pending, overdue.
    Query params:
      - project_id
      - from_date, to_date (YYYY-MM-DD)
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'analytics'

    @extend_schema(
        description='Revenue summary: bookings value, payment collections',
        parameters=[
            OpenApiParameter('project_id', int, required=False),
            OpenApiParameter('from_date', str, required=False),
            OpenApiParameter('to_date', str, required=False),
        ],
    )
    def get(self, request):
        tenant_id = _get_tenant(request)
        booking_qs = Booking.objects.filter(
            tenant_id=tenant_id
        ).exclude(status=BookingStatusEnum.CANCELLED)

        project_id = request.query_params.get('project_id')
        if project_id:
            booking_qs = booking_qs.filter(unit__tower__project_id=project_id)

        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        if from_date:
            booking_qs = booking_qs.filter(booking_date__gte=from_date)
        if to_date:
            booking_qs = booking_qs.filter(booking_date__lte=to_date)

        totals = booking_qs.aggregate(
            total_bookings=Count('id'),
            total_value=Sum('total_amount'),
        )

        milestone_qs = PaymentMilestone.objects.filter(
            tenant_id=tenant_id, booking__in=booking_qs
        )
        collection = milestone_qs.filter(
            status__in=[MilestoneStatusEnum.PAID, MilestoneStatusEnum.PARTIALLY_PAID]
        ).aggregate(collected=Sum('received_amount'))

        pending_qs = milestone_qs.filter(
            status__in=[MilestoneStatusEnum.PENDING, MilestoneStatusEnum.PARTIALLY_PAID,
                        MilestoneStatusEnum.OVERDUE]
        )
        pending = pending_qs.aggregate(pending=Sum('amount'))
        overdue = milestone_qs.filter(status=MilestoneStatusEnum.OVERDUE).aggregate(overdue=Sum('amount'))

        # Monthly trend (last 6 months)
        monthly = []
        today = timezone.now().date()
        for i in range(5, -1, -1):
            month_start = (today.replace(day=1) - datetime.timedelta(days=i * 30)).replace(day=1)
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1, day=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1, day=1)
            month_bookings = booking_qs.filter(
                booking_date__gte=month_start, booking_date__lt=month_end
            )
            monthly.append({
                'month': month_start.strftime('%b %Y'),
                'bookings': month_bookings.count(),
                'value': month_bookings.aggregate(v=Sum('total_amount'))['v'] or 0,
            })

        return Response({
            'total_bookings': totals['total_bookings'] or 0,
            'total_value': totals['total_value'] or 0,
            'collected': collection['collected'] or 0,
            'pending': pending['pending'] or 0,
            'overdue': overdue['overdue'] or 0,
            'monthly_trend': monthly,
        })


class AgentLeaderboardView(APIView):
    """
    Agent leaderboard: site visits, bookings, conversion rate per agent.
    Query params:
      - days: last N days (default: 30)
      - project_id
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'analytics'

    @extend_schema(
        description='Agent leaderboard: site visits, bookings, conversion rate',
        parameters=[
            OpenApiParameter('days', int, required=False),
            OpenApiParameter('project_id', int, required=False),
        ],
    )
    def get(self, request):
        tenant_id = _get_tenant(request)
        days = int(request.query_params.get('days', 30))
        cutoff = timezone.now() - datetime.timedelta(days=days)

        project_id = request.query_params.get('project_id')

        # Leads assigned to each agent
        leads_qs = Lead.objects.filter(
            tenant_id=tenant_id,
            created_at__gte=cutoff,
            assigned_to__isnull=False,
        )
        if project_id:
            leads_qs = leads_qs.filter(preferred_project_id=project_id)

        leads_per_agent = leads_qs.values('assigned_to').annotate(count=Count('id'))

        # Site visits per agent (distinct leads visited)
        visits_qs = LeadActivity.objects.filter(
            tenant_id=tenant_id,
            type=ActivityTypeEnum.SITE_VISIT,
            happened_at__gte=cutoff,
        )
        visits_per_agent = visits_qs.values('by_user_id').annotate(count=Count('lead', distinct=True))

        # Bookings per agent
        bookings_qs = Booking.objects.filter(
            tenant_id=tenant_id,
            booking_date__gte=cutoff.date(),
        ).exclude(status=BookingStatusEnum.CANCELLED)
        if project_id:
            bookings_qs = bookings_qs.filter(unit__tower__project_id=project_id)
        bookings_per_agent = bookings_qs.values('owner_user_id').annotate(count=Count('id'))

        # Merge results
        agent_map = {}
        for row in leads_per_agent:
            uid = str(row['assigned_to'])
            agent_map.setdefault(uid, {})['leads'] = row['count']
        for row in visits_per_agent:
            uid = str(row['by_user_id'])
            agent_map.setdefault(uid, {})['site_visits'] = row['count']
        for row in bookings_per_agent:
            uid = str(row['owner_user_id'])
            agent_map.setdefault(uid, {})['bookings'] = row['count']

        leaderboard = []
        for uid, stats in agent_map.items():
            leads = stats.get('leads', 0)
            bookings = stats.get('bookings', 0)
            conversion = round(bookings / leads * 100, 1) if leads else 0
            leaderboard.append({
                'user_id': uid,
                'leads_assigned': leads,
                'site_visits': stats.get('site_visits', 0),
                'bookings': bookings,
                'conversion_rate': conversion,
            })

        leaderboard.sort(key=lambda x: (-x['bookings'], -x['site_visits']))
        for i, row in enumerate(leaderboard, start=1):
            row['rank'] = i

        return Response({
            'period_days': days,
            'count': len(leaderboard),
            'results': leaderboard,
        })


class LeadSourceROIView(APIView):
    """
    Lead source ROI: which source brings the most closings.
    Shows leads, site visits, and bookings per source.
    Query params:
      - days: last N days (default: 90)
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'analytics'

    @extend_schema(
        description='Lead source ROI: leads, site visits, bookings per source',
        parameters=[OpenApiParameter('days', int, required=False)],
    )
    def get(self, request):
        tenant_id = _get_tenant(request)
        days = int(request.query_params.get('days', 90))
        cutoff = timezone.now() - datetime.timedelta(days=days)

        leads_qs = Lead.objects.filter(tenant_id=tenant_id, created_at__gte=cutoff)

        # Leads per source
        leads_by_source = leads_qs.values('re_source').annotate(leads=Count('id'))
        source_map = {}
        for row in leads_by_source:
            src = row['re_source'] or 'OTHER'
            source_map[src] = {'source': src, 'leads': row['leads'], 'site_visits': 0, 'bookings': 0}

        # Site visits per source (via lead's re_source)
        visits = LeadActivity.objects.filter(
            tenant_id=tenant_id,
            type=ActivityTypeEnum.SITE_VISIT,
            happened_at__gte=cutoff,
        ).values('lead__re_source').annotate(count=Count('lead', distinct=True))
        for row in visits:
            src = row['lead__re_source'] or 'OTHER'
            source_map.setdefault(src, {'source': src, 'leads': 0, 'site_visits': 0, 'bookings': 0})
            source_map[src]['site_visits'] = row['count']

        # Bookings per source (via lead's re_source)
        bookings = Booking.objects.filter(
            tenant_id=tenant_id,
            booking_date__gte=cutoff.date(),
        ).exclude(status=BookingStatusEnum.CANCELLED).values(
            'lead__re_source'
        ).annotate(count=Count('id'))
        for row in bookings:
            src = row['lead__re_source'] or 'OTHER'
            source_map.setdefault(src, {'source': src, 'leads': 0, 'site_visits': 0, 'bookings': 0})
            source_map[src]['bookings'] = row['count']

        results = sorted(source_map.values(), key=lambda x: -x['bookings'])
        # Conversion rates
        for row in results:
            row['visit_rate'] = round(row['site_visits'] / row['leads'] * 100, 1) if row['leads'] else 0
            row['booking_rate'] = round(row['bookings'] / row['leads'] * 100, 1) if row['leads'] else 0

        return Response({'period_days': days, 'results': results})


class DashboardOverviewView(APIView):
    """
    Single-call overview for the main builder dashboard.
    Returns:
      - inventory summary (overall unit counts)
      - funnel summary (total leads, won, lost, conversion)
      - revenue summary (total value, collected, pending)
      - top 5 agents (last 30 days)
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'analytics'

    @extend_schema(description='Main dashboard overview: inventory + funnel + revenue + top agents')
    def get(self, request):
        tenant_id = _get_tenant(request)
        today = timezone.now().date()

        # ---- Inventory ----
        unit_counts = Unit.objects.filter(
            tenant_id=tenant_id, is_active=True
        ).values('status').annotate(count=Count('id'))
        inventory = {row['status']: row['count'] for row in unit_counts}

        # ---- Funnel ----
        total_leads = Lead.objects.filter(tenant_id=tenant_id).count()
        new_leads_today = Lead.objects.filter(
            tenant_id=tenant_id, created_at__date=today
        ).count()
        won_leads = Lead.objects.filter(tenant_id=tenant_id, status__is_won=True).count()

        # ---- Revenue ----
        active_bookings = Booking.objects.filter(
            tenant_id=tenant_id
        ).exclude(status=BookingStatusEnum.CANCELLED)
        revenue = active_bookings.aggregate(
            bookings=Count('id'), total_value=Sum('total_amount')
        )
        collected = PaymentMilestone.objects.filter(
            tenant_id=tenant_id,
            booking__in=active_bookings,
            status__in=[MilestoneStatusEnum.PAID, MilestoneStatusEnum.PARTIALLY_PAID],
        ).aggregate(s=Sum('received_amount'))['s'] or 0

        # ---- Upcoming payments (next 7 days) ----
        upcoming = PaymentMilestone.objects.filter(
            tenant_id=tenant_id,
            status__in=[MilestoneStatusEnum.PENDING, MilestoneStatusEnum.PARTIALLY_PAID],
            due_date__gte=today,
            due_date__lte=today + datetime.timedelta(days=7),
        ).count()

        # ---- Site visits (last 7 days) ----
        seven_days_ago = timezone.now() - datetime.timedelta(days=7)
        site_visits_week = LeadActivity.objects.filter(
            tenant_id=tenant_id,
            type=ActivityTypeEnum.SITE_VISIT,
            happened_at__gte=seven_days_ago,
        ).count()

        return Response({
            'inventory': {
                'total': sum(inventory.values()),
                'available': inventory.get(UnitStatusEnum.AVAILABLE, 0),
                'reserved': inventory.get(UnitStatusEnum.RESERVED, 0),
                'booked': inventory.get(UnitStatusEnum.BOOKED, 0),
                'registered': inventory.get(UnitStatusEnum.REGISTERED, 0),
                'sold': inventory.get(UnitStatusEnum.SOLD, 0),
            },
            'leads': {
                'total': total_leads,
                'new_today': new_leads_today,
                'won': won_leads,
                'conversion_rate': round(won_leads / total_leads * 100, 1) if total_leads else 0,
            },
            'revenue': {
                'total_bookings': revenue['bookings'] or 0,
                'total_value': revenue['total_value'] or 0,
                'collected': collected,
                'pending': (revenue['total_value'] or 0) - collected,
            },
            'activity': {
                'site_visits_last_7_days': site_visits_week,
                'payments_due_next_7_days': upcoming,
            },
        })
