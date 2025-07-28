from django.db import models
from django.contrib.auth.models import User


# Temporarily simplified models to resolve circular dependency issues
# Will be restored after core migrations are created

class Dashboard(models.Model):
    """User dashboard configuration and summary data"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='dashboard',
        db_index=True
    )
    
    # Statistics (cached for performance)
    total_applications = models.PositiveIntegerField(default=0)
    active_applications = models.PositiveIntegerField(default=0)
    jobs_posted = models.PositiveIntegerField(default=0)
    profile_views = models.PositiveIntegerField(default=0)
    
    # Status counts for applications
    pending_applications = models.PositiveIntegerField(default=0)
    reviewed_applications = models.PositiveIntegerField(default=0)
    interview_applications = models.PositiveIntegerField(default=0)
    accepted_applications = models.PositiveIntegerField(default=0)
    rejected_applications = models.PositiveIntegerField(default=0)
    
    # Job posting stats (for employers)
    active_job_posts = models.PositiveIntegerField(default=0)
    total_job_applications_received = models.PositiveIntegerField(default=0)
    jobs_filled = models.PositiveIntegerField(default=0)
    
    # Preferences
    dashboard_layout = models.JSONField(
        default=dict, 
        blank=True,
        help_text="User's dashboard layout preferences"
    )
    notification_preferences = models.JSONField(
        default=dict, 
        blank=True,
        help_text="User's notification preferences"
    )
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True, db_index=True)
    stats_updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_dashboards'
    
    def __str__(self):
        return f"{self.user.username}'s Dashboard"
