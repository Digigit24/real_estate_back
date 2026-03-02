from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BrokerViewSet, CommissionViewSet

router = DefaultRouter()
router.register(r'brokers', BrokerViewSet, basename='broker')
router.register(r'commissions', CommissionViewSet, basename='commission')

urlpatterns = [
    path('', include(router.urls)),
]
