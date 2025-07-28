from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Response time tracking
    path('response-times/', views.ResponseTimeListCreateView.as_view(), name='response_time_list_create'),
    path('response-times/<int:pk>/', views.ResponseTimeDetailView.as_view(), name='response_time_detail'),
    
    # Performance analytics
    path('performance/endpoints/', views.endpoint_performance, name='endpoint_performance'),
    path('performance/trends/', views.performance_trends, name='performance_trends'),
    path('performance/database/', views.database_performance, name='database_performance'),
    path('performance/cache/', views.cache_performance, name='cache_performance'),
    
    # Error analysis
    path('errors/analysis/', views.error_analysis, name='error_analysis'),
    
    # System health
    path('health/', views.system_health, name='system_health'),
] 