from django.urls import path
from . import views

app_name = 'activity'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/summary/', views.dashboard_summary, name='dashboard_summary'),
    path('dashboard/reset/', views.reset_dashboard, name='reset_dashboard'),
    
    # Activity tracking
    path('timeline/', views.activity_timeline, name='activity_timeline'),
    path('metrics/', views.performance_metrics, name='performance_metrics'),
] 