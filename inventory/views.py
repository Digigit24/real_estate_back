from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count
from drf_spectacular.utils import extend_schema, extend_schema_view

from common.mixins import TenantViewSetMixin
from common.permissions import JWTAuthentication, HasCRMPermission
from .models import Project, Tower, Unit, UnitStatusEnum
from .serializers import (
    ProjectSerializer, ProjectListSerializer,
    TowerSerializer,
    UnitSerializer, UnitListSerializer,
    PriceCalculatorSerializer,
    UnitReserveSerializer,
    UnitStatusUpdateSerializer,
)
import logging

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(description='List all projects for the tenant'),
    retrieve=extend_schema(description='Retrieve a project with its towers'),
    create=extend_schema(description='Create a new project'),
    update=extend_schema(description='Update a project'),
    partial_update=extend_schema(description='Partially update a project'),
    destroy=extend_schema(description='Delete a project'),
)
class ProjectViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """ViewSet for managing real estate Projects."""
    queryset = Project.objects.prefetch_related('towers').all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'projects'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'city', 'state']
    search_fields = ['name', 'city', 'rera_number']
    ordering_fields = ['name', 'launch_date', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectListSerializer
        return ProjectSerializer

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        serializer.save(
            tenant_id=tenant_id,
            owner_user_id=self.request.user_id
        )

    @extend_schema(description='Get inventory summary for a project')
    @action(detail=True, methods=['get'], url_path='inventory-summary')
    def inventory_summary(self, request, pk=None):
        """Return unit count grouped by status for a project."""
        project = self.get_object()
        counts = (
            Unit.objects
            .filter(tower__project=project, tenant_id=request.tenant_id)
            .values('status')
            .annotate(count=Count('id'))
        )
        summary = {row['status']: row['count'] for row in counts}
        total = sum(summary.values())
        return Response({
            'project_id': project.id,
            'project_name': project.name,
            'total': total,
            'available': summary.get(UnitStatusEnum.AVAILABLE, 0),
            'reserved': summary.get(UnitStatusEnum.RESERVED, 0),
            'booked': summary.get(UnitStatusEnum.BOOKED, 0),
            'registered': summary.get(UnitStatusEnum.REGISTERED, 0),
            'sold': summary.get(UnitStatusEnum.SOLD, 0),
            'blocked': summary.get(UnitStatusEnum.BLOCKED, 0),
        })


@extend_schema_view(
    list=extend_schema(description='List towers for a project'),
    retrieve=extend_schema(description='Retrieve a tower'),
    create=extend_schema(description='Create a tower under a project'),
    update=extend_schema(description='Update a tower'),
    partial_update=extend_schema(description='Partially update a tower'),
    destroy=extend_schema(description='Delete a tower'),
)
class TowerViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """ViewSet for managing Towers within a Project."""
    queryset = Tower.objects.select_related('project').all()
    serializer_class = TowerSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'towers'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        serializer.save(tenant_id=tenant_id)

    @extend_schema(description='Get unit grid for this tower (floor x flat layout, ordered top to bottom)')
    @action(detail=True, methods=['get'], url_path='unit-grid')
    def unit_grid(self, request, pk=None):
        """
        Returns floors in descending order (top floor first).
        Each floor is a row of unit cells with status color info.
        """
        tower = self.get_object()
        units = (
            Unit.objects
            .filter(tower=tower, tenant_id=request.tenant_id, is_active=True)
            .order_by('floor_number', 'unit_number')
        )

        floors = {}
        for unit in units:
            floor = unit.floor_number
            if floor not in floors:
                floors[floor] = []
            floors[floor].append({
                'id': unit.id,
                'unit_number': unit.unit_number,
                'floor_number': unit.floor_number,
                'bhk_type': unit.bhk_type,
                'carpet_area': unit.carpet_area,
                'facing': unit.facing,
                'total_price': unit.total_price,
                'status': unit.status,
                'reserved_for_lead_id': unit.reserved_for_lead_id,
            })

        grid = [
            {'floor_number': floor_num, 'units': cells}
            for floor_num, cells in sorted(floors.items(), reverse=True)
        ]
        return Response({'tower_id': tower.id, 'tower_name': tower.name, 'grid': grid})


@extend_schema_view(
    list=extend_schema(description='List units with filtering'),
    retrieve=extend_schema(description='Retrieve unit details'),
    create=extend_schema(description='Create a unit'),
    update=extend_schema(description='Update a unit'),
    partial_update=extend_schema(description='Partially update a unit'),
    destroy=extend_schema(description='Delete a unit'),
)
class UnitViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing Units.

    Special actions:
    - POST /{id}/reserve/        - reserve unit for a lead
    - POST /{id}/release/        - release reservation
    - POST /{id}/update-status/  - manually set status
    - POST /price-calculator/    - compute total price from components
    - GET  /suggest/             - suggest units matching a lead
    """
    queryset = Unit.objects.select_related('tower', 'tower__project').all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'units'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'tower': ['exact'],
        'bhk_type': ['exact', 'in'],
        'status': ['exact', 'in'],
        'floor_number': ['exact', 'gte', 'lte'],
        'facing': ['exact'],
        'base_price': ['gte', 'lte'],
        'is_active': ['exact'],
    }
    search_fields = ['unit_number', 'bhk_type']
    ordering_fields = ['floor_number', 'unit_number', 'base_price', 'status', 'created_at']
    ordering = ['floor_number', 'unit_number']

    def get_serializer_class(self):
        if self.action == 'list':
            return UnitListSerializer
        return UnitSerializer

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        serializer.save(
            tenant_id=tenant_id,
            owner_user_id=self.request.user_id
        )

    @extend_schema(
        description='Reserve a unit for a lead. Unit must be AVAILABLE. Sets status to RESERVED.',
        request=UnitReserveSerializer,
    )
    @action(detail=True, methods=['post'], url_path='reserve')
    def reserve(self, request, pk=None):
        unit = self.get_object()

        if unit.status != UnitStatusEnum.AVAILABLE:
            return Response(
                {'error': f'Unit is not available. Current status: {unit.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = UnitReserveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        unit.status = UnitStatusEnum.RESERVED
        unit.reserved_for_lead_id = serializer.validated_data['lead_id']
        unit.save(update_fields=['status', 'reserved_for_lead_id', 'updated_at'])

        return Response(UnitSerializer(unit, context={'request': request}).data)

    @extend_schema(
        description='Release a unit reservation, setting it back to AVAILABLE. No request body needed.',
        request=None,
        responses={200: UnitSerializer, 400: {'description': 'Unit is not currently RESERVED'}},
    )
    @action(detail=True, methods=['post'], url_path='release')
    def release(self, request, pk=None):
        unit = self.get_object()

        if unit.status != UnitStatusEnum.RESERVED:
            return Response(
                {'error': f'Unit is not reserved. Current status: {unit.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        unit.status = UnitStatusEnum.AVAILABLE
        unit.reserved_for_lead_id = None
        unit.save(update_fields=['status', 'reserved_for_lead_id', 'updated_at'])

        return Response(UnitSerializer(unit, context={'request': request}).data)

    @extend_schema(
        description='Update unit status manually (admin override).',
        request=UnitStatusUpdateSerializer,
    )
    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        unit = self.get_object()
        serializer = UnitStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        unit.status = serializer.validated_data['status']
        lead_id = serializer.validated_data.get('lead_id')
        if lead_id is not None:
            unit.reserved_for_lead_id = lead_id
        unit.save(update_fields=['status', 'reserved_for_lead_id', 'updated_at'])

        return Response(UnitSerializer(unit, context={'request': request}).data)

    @extend_schema(
        description='Calculate total price from individual price components.',
        request=PriceCalculatorSerializer,
    )
    @action(detail=False, methods=['post'], url_path='price-calculator')
    def price_calculator(self, request):
        serializer = PriceCalculatorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        total = (
            d['base_price']
            + d.get('floor_rise_premium', 0)
            + d.get('facing_premium', 0)
            + d.get('parking_charges', 0)
            + d.get('other_charges', 0)
        )
        return Response({**d, 'total_price': total})

    @extend_schema(
        description=(
            'Suggest available units matching a lead\'s budget and BHK preference. '
            'Query params: lead_id (required), project_id (optional).'
        )
    )
    @action(detail=False, methods=['get'], url_path='suggest')
    def suggest(self, request):
        """Return available units matching the budget + BHK preference of a lead."""
        lead_id = request.query_params.get('lead_id')
        if not lead_id:
            return Response(
                {'error': 'lead_id query param is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        from crm.models import Lead
        try:
            lead = Lead.objects.get(id=lead_id, tenant_id=request.tenant_id)
        except Lead.DoesNotExist:
            return Response({'error': 'Lead not found'}, status=status.HTTP_404_NOT_FOUND)

        qs = Unit.objects.filter(
            tenant_id=request.tenant_id,
            status=UnitStatusEnum.AVAILABLE,
            is_active=True,
        ).select_related('tower', 'tower__project')

        project_id = request.query_params.get('project_id') or lead.preferred_project_id
        if project_id:
            qs = qs.filter(tower__project_id=project_id)

        if lead.bhk_preference:
            qs = qs.filter(bhk_type=lead.bhk_preference)

        if lead.budget_min is not None:
            qs = qs.filter(base_price__gte=lead.budget_min)
        if lead.budget_max is not None:
            qs = qs.filter(base_price__lte=lead.budget_max)

        units = qs[:20]
        return Response({
            'lead_id': lead.id,
            'bhk_preference': lead.bhk_preference,
            'budget_min': lead.budget_min,
            'budget_max': lead.budget_max,
            'suggestions': UnitListSerializer(units, many=True, context={'request': request}).data,
        })
