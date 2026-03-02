from django.urls import path
from .views import (
    InventoryHealthView,
    SalesFunnelView,
    RevenueView,
    AgentLeaderboardView,
    LeadSourceROIView,
    DashboardOverviewView,
)

urlpatterns = [
    path('overview/', DashboardOverviewView.as_view(), name='analytics-overview'),
    path('inventory/', InventoryHealthView.as_view(), name='analytics-inventory'),
    path('sales-funnel/', SalesFunnelView.as_view(), name='analytics-sales-funnel'),
    path('revenue/', RevenueView.as_view(), name='analytics-revenue'),
    path('agent-leaderboard/', AgentLeaderboardView.as_view(), name='analytics-agent-leaderboard'),
    path('lead-sources/', LeadSourceROIView.as_view(), name='analytics-lead-sources'),
]
