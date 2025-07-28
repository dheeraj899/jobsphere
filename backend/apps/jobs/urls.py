from django.urls import path
from . import views

app_name = 'jobs'

urlpatterns = [
    # Job management
    path('', views.JobListCreateView.as_view(), name='job_list_create'),
    path('<int:pk>/', views.JobDetailView.as_view(), name='job_detail'),
    path('my-jobs/', views.my_jobs, name='my_jobs'),
    path('categories/', views.job_categories, name='job_categories'),
    
    # Job applications
    path('applications/', views.JobApplicationListCreateView.as_view(), name='application_list_create'),
    path('applications/<int:pk>/', views.JobApplicationDetailView.as_view(), name='application_detail'),
    path('applications/<int:application_id>/withdraw/', views.withdraw_application, name='withdraw_application'),
    path('applications/stats/', views.application_stats, name='application_stats'),
    
    # Saved jobs
    path('saved/', views.SavedJobListCreateView.as_view(), name='saved_job_list_create'),
    path('saved/<int:pk>/', views.SavedJobDetailView.as_view(), name='saved_job_detail'),
] 