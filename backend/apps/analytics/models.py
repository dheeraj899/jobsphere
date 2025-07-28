from django.db import models
from django.contrib.auth.models import User

# Temporarily simplified models to resolve circular dependency issues
# Will be restored after core migrations are created


class ResponseTime(models.Model):
    """Track API response times and system performance"""
    ENDPOINT_CATEGORIES = [
        ('authentication', 'Authentication'),
        ('jobs', 'Jobs'),
        ('profile', 'Profile'),
        ('search', 'Search'),
        ('messaging', 'Messaging'),
        ('media', 'Media'),
        ('analytics', 'Analytics'),
        ('other', 'Other'),
    ]
    
    # Request info
    endpoint = models.CharField(max_length=200, db_index=True)
    http_method = models.CharField(max_length=10, db_index=True)
    endpoint_category = models.CharField(max_length=20, choices=ENDPOINT_CATEGORIES, db_index=True)
    
    # Performance metrics
    response_time_ms = models.PositiveIntegerField(help_text="Response time in milliseconds", db_index=True)
    db_query_time_ms = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Database query time in milliseconds"
    )
    db_query_count = models.PositiveIntegerField(default=0)
    cache_hit = models.BooleanField(null=True, blank=True, db_index=True)
    
    # Response info
    status_code = models.PositiveIntegerField(db_index=True)
    response_size_bytes = models.PositiveIntegerField(null=True, blank=True)
    
    # User context
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_index=True
    )
    ip_address = models.GenericIPAddressField(db_index=True)
    user_agent = models.TextField(blank=True)
    
    # Server info
    server_name = models.CharField(max_length=100, blank=True, db_index=True)
    process_id = models.PositiveIntegerField(null=True, blank=True)
    
    # Error tracking
    has_error = models.BooleanField(default=False, db_index=True)
    error_type = models.CharField(max_length=100, blank=True, db_index=True)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'response_times'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['endpoint', '-timestamp']),
            models.Index(fields=['endpoint_category', '-timestamp']),
            models.Index(fields=['http_method', 'status_code']),
            models.Index(fields=['-response_time_ms']),
            models.Index(fields=['has_error', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['cache_hit', 'response_time_ms']),
        ]
    
    def __str__(self):
        return f"{self.http_method} {self.endpoint} - {self.response_time_ms}ms"
    
    @property
    def is_slow(self):
        """Check if response time is considered slow (>2000ms)"""
        return self.response_time_ms > 2000
    
    @property
    def performance_grade(self):
        """Return performance grade based on response time"""
        if self.response_time_ms < 200:
            return 'A'
        elif self.response_time_ms < 500:
            return 'B'
        elif self.response_time_ms < 1000:
            return 'C'
        elif self.response_time_ms < 2000:
            return 'D'
        else:
            return 'F'
