from django.contrib import admin
from django.urls import path
from django.template.response import TemplateResponse
from django.contrib.auth import get_user_model
from apps.profile.models import UserProfile, Experience
from apps.jobs.models import Job, JobApplication
from apps.messaging.models import Notification
from apps.search.models import SearchQuery

# Extend the admin site URLs to include a custom dashboard
original_urls = admin.site.get_urls
def get_urls():
    urls = [
        path('dashboard/', admin.site.admin_view(dashboard_view), name='dashboard'),
    ]
    return urls + original_urls()

admin.site.get_urls = get_urls

def dashboard_view(request):
    User = get_user_model()
    stats = {
        'total_users': User.objects.count(),
        'total_profiles': UserProfile.objects.count(),
        'total_experiences': Experience.objects.count(),
        'total_jobs': Job.objects.count(),
        'total_applications': JobApplication.objects.count(),
        'total_notifications': Notification.objects.count(),
        'total_searches': SearchQuery.objects.count(),
    }
    context = {**admin.site.each_context(request), 'stats': stats}
    return TemplateResponse(request, 'admin/dashboard.html', context)

from .models import ResponseTime

@admin.register(ResponseTime)
class ResponseTimeAdmin(admin.ModelAdmin):
    list_display = ('endpoint_category', 'http_method', 'status_code', 'response_time_ms', 'timestamp')
    list_filter = ('endpoint_category', 'status_code')
    search_fields = ('endpoint',)
