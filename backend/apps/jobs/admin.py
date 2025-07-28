from django.contrib import admin
from .models import Job, JobApplication, JobView, SavedJob

class JobApplicationInline(admin.TabularInline):
    model = JobApplication
    extra = 0

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'posted_by', 'status', 'published_at')
    list_filter = ('job_type', 'status', 'experience_level')
    search_fields = ('title', 'company')
    inlines = (JobApplicationInline,)

@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('job', 'applicant', 'status', 'applied_at')
    list_filter = ('status',)
    search_fields = ('job__title', 'applicant__username')

@admin.register(JobView)
class JobViewAdmin(admin.ModelAdmin):
    list_display = ('job', 'user', 'ip_address', 'viewed_at')
    list_filter = ('viewed_at',)
    search_fields = ('job__title', 'user__username')

@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ('job', 'user', 'saved_at')
    list_filter = ('saved_at',)
    search_fields = ('job__title', 'user__username')
