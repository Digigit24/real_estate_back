from django.db.models import Sum, Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.mixins import TenantViewSetMixin
from common.permissions import JWTAuthentication, HasCRMPermission
from .authentication import BrokerTokenAuthentication
from .models import Broker, Commission, CommissionStatusEnum, BrokerStatusEnum, BrokerSession
from .serializers import (
    BrokerSerializer, BrokerListSerializer,
    CommissionSerializer, CommissionCreateSerializer, CommissionMarkPaidSerializer,
)
import logging

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(description='List all channel partners / brokers'),
    retrieve=extend_schema(description='Get broker detail with leads and commissions summary'),
    create=extend_schema(description='Register a new broker'),
    update=extend_schema(description='Update broker details'),
    partial_update=extend_schema(description='Partially update broker details'),
    destroy=extend_schema(description='Delete a broker'),
)
class BrokerViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for Channel Partner / Broker management.

    Special actions:
    - GET  /leaderboard/        — broker leaderboard sorted by bookings/commissions
    - GET  /{id}/leads/         — leads submitted by this broker
    - GET  /{id}/commissions/   — commissions for this broker
    """
    queryset = Broker.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'brokers'
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'city']
    search_fields = ['name', 'phone', 'email', 'company_name', 'rera_number']
    ordering_fields = ['name', 'created_at', 'commission_rate']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return BrokerListSerializer
        return BrokerSerializer

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        serializer.save(tenant_id=tenant_id, owner_user_id=self.request.user_id)

    @extend_schema(description='Broker leaderboard: sorted by bookings count and total commission')
    @action(detail=False, methods=['get'], url_path='leaderboard')
    def leaderboard(self, request):
        tenant_id = request.tenant_id
        brokers = Broker.objects.filter(
            tenant_id=tenant_id,
            status=BrokerStatusEnum.ACTIVE,
        ).annotate(
            bookings_count=Count('commissions', filter=Q(commissions__status__in=[
                CommissionStatusEnum.PENDING, CommissionStatusEnum.PAID
            ])),
            total_commission=Sum('commissions__commission_amount', filter=Q(
                commissions__status__in=[CommissionStatusEnum.PENDING, CommissionStatusEnum.PAID]
            )),
            leads_count=Count('id'),  # placeholder; real count done via CRM
        ).order_by('-bookings_count', '-total_commission')

        data = []
        for rank, broker in enumerate(brokers, start=1):
            from crm.models import Lead
            leads_count = Lead.objects.filter(tenant_id=tenant_id, broker_id=broker.id).count()
            data.append({
                'rank': rank,
                'broker_id': broker.id,
                'name': broker.name,
                'phone': broker.phone,
                'company_name': broker.company_name,
                'bookings_count': broker.bookings_count or 0,
                'total_commission': broker.total_commission or 0,
                'leads_count': leads_count,
            })
        return Response({'count': len(data), 'results': data})

    @extend_schema(description='Get all leads submitted / attributed to this broker')
    @action(detail=True, methods=['get'], url_path='leads')
    def leads(self, request, pk=None):
        broker = self.get_object()
        from crm.models import Lead
        from crm.serializers import LeadListSerializer
        leads = Lead.objects.filter(
            tenant_id=request.tenant_id,
            broker_id=broker.id,
        ).select_related('status')
        return Response(LeadListSerializer(leads, many=True, context={'request': request}).data)

    @extend_schema(description='Get all commissions for this broker')
    @action(detail=True, methods=['get'], url_path='commissions')
    def broker_commissions(self, request, pk=None):
        broker = self.get_object()
        commissions = broker.commissions.select_related(
            'booking', 'booking__unit', 'booking__unit__tower', 'booking__unit__tower__project'
        ).all()
        return Response(CommissionSerializer(commissions, many=True).data)


@extend_schema_view(
    list=extend_schema(description='List all commissions'),
    retrieve=extend_schema(description='Get commission detail'),
    create=extend_schema(description='Create a commission record for a broker booking'),
    update=extend_schema(description='Update commission details'),
    partial_update=extend_schema(description='Partially update commission'),
    destroy=extend_schema(description='Delete a commission record'),
)
class CommissionViewSet(TenantViewSetMixin, viewsets.ModelViewSet):
    """
    ViewSet for Commission management.

    Special actions:
    - POST /{id}/mark-paid/ — mark commission as paid
    """
    queryset = Commission.objects.select_related(
        'broker', 'booking', 'booking__unit', 'booking__unit__tower', 'booking__unit__tower__project'
    ).all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [HasCRMPermission]
    permission_resource = 'commissions'
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = {
        'status': ['exact', 'in'],
        'broker': ['exact'],
        'booking': ['exact'],
    }
    ordering_fields = ['created_at', 'commission_amount', 'paid_date']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return CommissionCreateSerializer
        return CommissionSerializer

    def perform_create(self, serializer):
        tenant_id = getattr(self.request, 'tenant_id', None)
        serializer.save(tenant_id=tenant_id, owner_user_id=self.request.user_id)

    @extend_schema(
        description='Mark commission as paid',
        request=CommissionMarkPaidSerializer,
    )
    @action(detail=True, methods=['post'], url_path='mark-paid')
    def mark_paid(self, request, pk=None):
        commission = self.get_object()
        serializer = CommissionMarkPaidSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        commission.status = CommissionStatusEnum.PAID
        commission.paid_date = serializer.validated_data['paid_date']
        if serializer.validated_data.get('notes'):
            commission.notes = serializer.validated_data['notes']
        commission.save(update_fields=['status', 'paid_date', 'notes', 'updated_at'])
        return Response(CommissionSerializer(commission).data)


# ---------------------------------------------------------------------------
# Broker Portal Auth Views
# ---------------------------------------------------------------------------

class BrokerRegisterView(APIView):
    """
    POST /api/brokers/portal/register/
    Broker self-registration. Creates broker in PENDING status.
    Builder admin must approve (set status=ACTIVE) before broker can login.
    Body: { tenant_id, name, phone, email, password, company_name, rera_number, city }
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(description='Broker self-registration (status=PENDING until approved by admin)')
    def post(self, request):
        data = request.data
        required = ['tenant_id', 'name', 'phone', 'password']
        missing = [f for f in required if not data.get(f)]
        if missing:
            return Response({'error': f'Missing fields: {", ".join(missing)}'}, status=status.HTTP_400_BAD_REQUEST)

        tenant_id = data['tenant_id']
        phone = data['phone']

        if Broker.objects.filter(tenant_id=tenant_id, phone=phone).exists():
            return Response({'error': 'A broker with this phone already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        if data.get('email'):
            if Broker.objects.filter(tenant_id=tenant_id, portal_email=data['email']).exists():
                return Response({'error': 'A broker with this email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        broker = Broker(
            tenant_id=tenant_id,
            name=data['name'],
            phone=phone,
            email=data.get('email'),
            portal_email=data.get('email'),
            company_name=data.get('company_name'),
            rera_number=data.get('rera_number'),
            city=data.get('city'),
            status=BrokerStatusEnum.PENDING,
            owner_user_id='00000000-0000-0000-0000-000000000000',  # system
        )
        broker.set_password(data['password'])
        broker.save()

        return Response({
            'message': 'Registration successful. Your account is pending approval by the builder.',
            'broker_id': broker.id,
            'status': broker.status,
        }, status=status.HTTP_201_CREATED)


class BrokerLoginView(APIView):
    """
    POST /api/brokers/portal/login/
    Body: { tenant_id, phone, password }
    Returns: { token, broker_id, name, status }
    """
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(description='Broker portal login — returns BrokerToken for subsequent requests')
    def post(self, request):
        tenant_id = request.data.get('tenant_id')
        phone = request.data.get('phone')
        password = request.data.get('password')

        if not all([tenant_id, phone, password]):
            return Response({'error': 'tenant_id, phone, and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            broker = Broker.objects.get(tenant_id=tenant_id, phone=phone)
        except Broker.DoesNotExist:
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        if not broker.check_password(password):
            return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        if broker.status == BrokerStatusEnum.PENDING:
            return Response({'error': 'Your account is pending approval by the builder.'}, status=status.HTTP_403_FORBIDDEN)

        if broker.status != BrokerStatusEnum.ACTIVE:
            return Response({'error': f'Account is {broker.status}. Contact the builder.'}, status=status.HTTP_403_FORBIDDEN)

        session = BrokerSession.create_for_broker(broker)
        return Response({
            'token': session.token,
            'broker_id': broker.id,
            'name': broker.name,
            'phone': broker.phone,
            'company_name': broker.company_name,
            'status': broker.status,
            'expires_at': session.expires_at,
        })


class BrokerLogoutView(APIView):
    """POST /api/brokers/portal/logout/ — invalidate current token"""
    authentication_classes = [BrokerTokenAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(description='Broker portal logout — invalidates the current session token')
    def post(self, request):
        auth = request.auth
        if auth and isinstance(auth, BrokerSession):
            auth.delete()
        return Response({'message': 'Logged out successfully.'})


class BrokerMeView(APIView):
    """GET /api/brokers/portal/me/ — get authenticated broker's own profile + stats"""
    authentication_classes = [BrokerTokenAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(description='Get authenticated broker profile with leads count, bookings, and commissions summary')
    def get(self, request):
        broker = request.broker
        from crm.models import Lead
        leads_count = Lead.objects.filter(tenant_id=broker.tenant_id, broker_id=broker.id).count()
        commissions = broker.commissions.all()
        total_commission = commissions.filter(
            status__in=[CommissionStatusEnum.PENDING, CommissionStatusEnum.PAID]
        ).aggregate(t=Sum('commission_amount'))['t'] or 0
        paid_commission = commissions.filter(
            status=CommissionStatusEnum.PAID
        ).aggregate(t=Sum('commission_amount'))['t'] or 0

        return Response({
            'id': broker.id,
            'name': broker.name,
            'phone': broker.phone,
            'email': broker.email,
            'company_name': broker.company_name,
            'rera_number': broker.rera_number,
            'commission_rate': broker.commission_rate,
            'status': broker.status,
            'city': broker.city,
            'stats': {
                'leads_submitted': leads_count,
                'bookings': commissions.count(),
                'total_commission_earned': total_commission,
                'commission_paid': paid_commission,
                'commission_pending': total_commission - paid_commission,
            },
        })


class BrokerSubmitLeadView(APIView):
    """
    POST /api/brokers/portal/submit-lead/
    Broker submits a buyer lead. It appears in the builder's CRM tagged to this broker.
    Auth: BrokerToken <token>
    """
    authentication_classes = [BrokerTokenAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(description='Broker submits a new buyer lead into the builder CRM (tagged to this broker)')
    def post(self, request):
        broker = request.broker
        data = request.data

        if not data.get('name') or not data.get('phone'):
            return Response({'error': 'name and phone are required.'}, status=status.HTTP_400_BAD_REQUEST)

        from crm.models import Lead
        lead = Lead.objects.create(
            tenant_id=broker.tenant_id,
            name=data['name'],
            phone=data['phone'],
            email=data.get('email'),
            re_source='BROKER',
            broker_id=broker.id,
            budget_min=data.get('budget_min'),
            budget_max=data.get('budget_max'),
            bhk_preference=data.get('bhk_preference'),
            preferred_project_id=data.get('preferred_project_id'),
            notes=data.get('notes', f'Lead submitted by broker: {broker.name}'),
            owner_user_id=str(broker.tenant_id),  # system-owned until assigned
            assigned_to=None,
        )
        return Response({
            'message': 'Lead submitted successfully. The builder\'s team will follow up.',
            'lead_id': lead.id,
            'lead_name': lead.name,
            'lead_phone': lead.phone,
        }, status=status.HTTP_201_CREATED)


class BrokerMyLeadsView(APIView):
    """GET /api/brokers/portal/my-leads/ — broker sees all leads they submitted"""
    authentication_classes = [BrokerTokenAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(description='Broker views their own submitted leads with current pipeline status')
    def get(self, request):
        broker = request.broker
        from crm.models import Lead
        leads = Lead.objects.filter(
            tenant_id=broker.tenant_id, broker_id=broker.id
        ).select_related('status').order_by('-created_at')
        data = [{
            'id': l.id,
            'name': l.name,
            'phone': l.phone,
            'budget_min': l.budget_min,
            'budget_max': l.budget_max,
            'bhk_preference': l.bhk_preference,
            'stage': l.status.name if l.status else None,
            'created_at': l.created_at,
        } for l in leads]
        return Response({'count': len(data), 'results': data})


class BrokerMyCommissionsView(APIView):
    """GET /api/brokers/portal/my-commissions/ — broker sees their own commissions"""
    authentication_classes = [BrokerTokenAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(description='Broker views their commission records per booking')
    def get(self, request):
        broker = request.broker
        commissions = broker.commissions.select_related(
            'booking', 'booking__unit', 'booking__unit__tower', 'booking__unit__tower__project'
        ).order_by('-created_at')
        data = [{
            'id': c.id,
            'booking_id': c.booking_id,
            'unit': c.booking.unit.unit_number,
            'project': c.booking.unit.tower.project.name,
            'booking_date': c.booking.booking_date,
            'booking_value': c.booking.total_amount,
            'commission_rate': c.commission_rate,
            'commission_amount': c.commission_amount,
            'status': c.status,
            'paid_date': c.paid_date,
        } for c in commissions]
        return Response({'count': len(data), 'results': data})
