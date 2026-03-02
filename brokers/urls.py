from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    BrokerViewSet, CommissionViewSet,
    BrokerRegisterView, BrokerLoginView, BrokerLogoutView,
    BrokerMeView, BrokerSubmitLeadView, BrokerMyLeadsView, BrokerMyCommissionsView,
)

router = DefaultRouter()
router.register(r'brokers', BrokerViewSet, basename='broker')
router.register(r'commissions', CommissionViewSet, basename='commission')

urlpatterns = [
    # Broker Portal Auth (no JWT required — uses BrokerToken)
    path('portal/register/', BrokerRegisterView.as_view(), name='broker-register'),
    path('portal/login/', BrokerLoginView.as_view(), name='broker-login'),
    path('portal/logout/', BrokerLogoutView.as_view(), name='broker-logout'),
    path('portal/me/', BrokerMeView.as_view(), name='broker-me'),
    path('portal/submit-lead/', BrokerSubmitLeadView.as_view(), name='broker-submit-lead'),
    path('portal/my-leads/', BrokerMyLeadsView.as_view(), name='broker-my-leads'),
    path('portal/my-commissions/', BrokerMyCommissionsView.as_view(), name='broker-my-commissions'),

    # Builder-side management (JWT required)
    path('', include(router.urls)),
]
