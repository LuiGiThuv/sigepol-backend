"""
Dashboard URLs - Admin analytics and statistics endpoints
PASO 8: Dashboard routes
"""

from django.urls import path
from .views import (
    AdminSystemStatsView,
    AdminBusinessStatsView,
    AdminRecentActivityView,
    AdminETLStatsView,
    AdminAlertSummaryView,
    AdminDashboardOverviewView,
)

urlpatterns = [
    # System statistics (PASO 8.1)
    path('stats/system/', AdminSystemStatsView.as_view(), name='system-stats'),

    # Business metrics (PASO 8.2)
    path('stats/business/', AdminBusinessStatsView.as_view(), name='business-stats'),

    # Recent activity/Audit logs (PASO 8.3)
    path('stats/activity/', AdminRecentActivityView.as_view(), name='recent-activity'),

    # ETL performance (PASO 8.4)
    path('stats/etl/', AdminETLStatsView.as_view(), name='etl-stats'),

    # Alerts summary (PASO 8.5)
    path('stats/alertas/', AdminAlertSummaryView.as_view(), name='alert-summary'),

    # Complete overview (PASO 8.6)
    path('overview/', AdminDashboardOverviewView.as_view(), name='dashboard-overview'),
]
