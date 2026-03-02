from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TenantSettingsView, PaymentPlanTemplateViewSet

router = DefaultRouter()
router.register(r'payment-plan-templates', PaymentPlanTemplateViewSet, basename='paymentplantemplate')

urlpatterns = [
    path('settings/', TenantSettingsView.as_view(), name='tenant-settings'),
    path('', include(router.urls)),
]
