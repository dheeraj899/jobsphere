from django.contrib import admin
from .models import Dashboard

@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_applications', 'jobs_posted', 'profile_views')
    search_fields = ('user__username',)
