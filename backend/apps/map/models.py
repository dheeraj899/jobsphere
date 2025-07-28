from django.db import models
from django.contrib.auth.models import User


class Region(models.Model):
    """Geographical regions for organizing locations"""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    code = models.CharField(max_length=10, unique=True)  # e.g., 'NYC', 'SF', 'LA'
    country = models.CharField(max_length=100, db_index=True)
    state_province = models.CharField(max_length=100, blank=True)
    
    # Geographical boundaries (simplified - in production might use PostGIS)
    latitude_min = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    latitude_max = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_min = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_max = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Regional settings
    timezone = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'regions'
        indexes = [
            models.Index(fields=['country', 'state_province']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.country})"


class Location(models.Model):
    """Specific locations for jobs, users, etc."""
    LOCATION_TYPES = [
        ('job', 'Job Location'),
        ('user', 'User Location'),
        ('company', 'Company Location'),
        ('event', 'Event Location'),
    ]
    
    # Basic location info
    name = models.CharField(max_length=200, db_index=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, db_index=True)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, db_index=True)
    
    # Coordinates for mapping
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True,
        db_index=True
    )
    longitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        null=True, 
        blank=True,
        db_index=True
    )
    
    # Classification
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES, db_index=True)
    region = models.ForeignKey(
        Region, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='locations',
        db_index=True
    )
    
    # Metadata
    is_verified = models.BooleanField(default=False, db_index=True)
    is_remote_friendly = models.BooleanField(default=False, db_index=True)
    
    # Reference tracking
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_index=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'locations'
        indexes = [
            models.Index(fields=['city', 'state_province', 'country']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['location_type', 'is_verified']),
            models.Index(fields=['region', 'location_type']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.name}, {self.city}"
    
    @property
    def full_address(self):
        """Return formatted full address"""
        parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state_province,
            self.postal_code,
            self.country
        ]
        return ', '.join([part for part in parts if part])


class LocationHistory(models.Model):
    """Track location searches and popular locations"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='location_searches',
        db_index=True
    )
    location = models.ForeignKey(
        Location, 
        on_delete=models.CASCADE, 
        related_name='search_history',
        db_index=True
    )
    search_query = models.CharField(max_length=200, blank=True)
    
    # Context
    search_context = models.CharField(
        max_length=50, 
        choices=[
            ('job_search', 'Job Search'),
            ('profile_update', 'Profile Update'),
            ('location_browse', 'Location Browse'),
        ],
        db_index=True
    )
    
    # Timestamps
    searched_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'location_history'
        indexes = [
            models.Index(fields=['user', '-searched_at']),
            models.Index(fields=['location', '-searched_at']),
            models.Index(fields=['search_context', '-searched_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} searched {self.location.name}"
