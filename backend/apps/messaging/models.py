from django.db import models
from django.contrib.auth.models import User

# Temporarily simplified models to resolve circular dependency issues
# Will be restored after core migrations are created


class Notification(models.Model):
    """System notifications for users"""
    NOTIFICATION_TYPES = [
        ('job_application', 'Job Application'),
        ('application_status', 'Application Status'),
        ('message', 'New Message'),
        ('job_posting', 'Job Posting'),
        ('interview', 'Interview'),
        ('system', 'System'),
        ('profile', 'Profile'),
        ('payment', 'Payment'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Recipients
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications',
        db_index=True
    )
    
    # Notification details
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, db_index=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='normal', db_index=True)
    
    # Action/Links
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=100, blank=True)
    
    # Related objects (generic)
    related_object_type = models.CharField(max_length=50, blank=True, db_index=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    
    # Status
    is_read = models.BooleanField(default=False, db_index=True)
    is_dismissed = models.BooleanField(default=False, db_index=True)
    
    # Delivery channels
    email_sent = models.BooleanField(default=False)
    push_sent = models.BooleanField(default=False)
    sms_sent = models.BooleanField(default=False)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
            models.Index(fields=['priority', 'is_read']),
            models.Index(fields=['related_object_type', 'related_object_id']),
            models.Index(fields=['expires_at', 'is_read']),
        ]
    
    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"
