from django.db import models
from django.contrib.auth.models import User
from apps.map.models import Location


class Category(models.Model):
    """Job categories for organizing and filtering jobs"""
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    
    # Hierarchy
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='subcategories',
        db_index=True
    )
    level = models.PositiveIntegerField(default=0, db_index=True)  # 0 = top level
    
    # Display and organization
    icon = models.CharField(max_length=50, blank=True)  # Icon CSS class or filename
    color = models.CharField(max_length=7, blank=True)  # Hex color code
    order = models.PositiveIntegerField(default=0, db_index=True)
    
    # Metadata
    is_active = models.BooleanField(default=True, db_index=True)
    job_count = models.PositiveIntegerField(default=0)  # Cached count
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'categories'
        ordering = ['level', 'order', 'name']
        indexes = [
            models.Index(fields=['parent', 'is_active']),
            models.Index(fields=['level', 'order']),
            models.Index(fields=['is_active', 'job_count']),
        ]
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    @property
    def full_path(self):
        """Return full category path"""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name


class SearchQuery(models.Model):
    """Track search queries for analytics and suggestions"""
    # Query details
    query_text = models.CharField(max_length=500, db_index=True)
    normalized_query = models.CharField(max_length=500, db_index=True)  # Cleaned/normalized version
    
    # User info (optional for anonymous searches)
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='search_queries',
        db_index=True
    )
    session_id = models.CharField(max_length=100, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(db_index=True)
    
    # Search context
    search_type = models.CharField(
        max_length=30,
        choices=[
            ('job_search', 'Job Search'),
            ('location_search', 'Location Search'),
            ('company_search', 'Company Search'),
            ('skill_search', 'Skill Search'),
            ('category_search', 'Category Search'),
        ],
        db_index=True
    )
    
    # Filters applied
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_index=True
    )
    location = models.ForeignKey(
        Location, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_index=True
    )
    job_type = models.CharField(max_length=20, blank=True, db_index=True)
    experience_level = models.CharField(max_length=20, blank=True, db_index=True)
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_remote = models.BooleanField(null=True, blank=True)
    
    # Results
    results_count = models.PositiveIntegerField(default=0, db_index=True)
    has_results = models.BooleanField(default=True, db_index=True)
    
    # User interaction
    clicked_result_position = models.PositiveIntegerField(null=True, blank=True)
    clicked_result_id = models.PositiveIntegerField(null=True, blank=True)
    time_spent = models.DurationField(null=True, blank=True)  # Time on search results page
    
    # Metadata
    user_agent = models.TextField(blank=True)
    referrer = models.URLField(blank=True)
    
    # Timestamps
    searched_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'search_queries'
        ordering = ['-searched_at']
        indexes = [
            models.Index(fields=['query_text', '-searched_at']),
            models.Index(fields=['normalized_query', '-searched_at']),
            models.Index(fields=['user', '-searched_at']),
            models.Index(fields=['search_type', '-searched_at']),
            models.Index(fields=['category', '-searched_at']),
            models.Index(fields=['location', '-searched_at']),
            models.Index(fields=['has_results', 'results_count']),
            models.Index(fields=['ip_address', '-searched_at']),
        ]
    
    def __str__(self):
        user_info = self.user.username if self.user else self.ip_address
        return f"{user_info} searched: {self.query_text}"


class PopularSearch(models.Model):
    """Popular/trending searches for suggestions"""
    query_text = models.CharField(max_length=500, unique=True, db_index=True)
    search_count = models.PositiveIntegerField(default=0, db_index=True)
    
    # Time-based metrics
    daily_count = models.PositiveIntegerField(default=0)
    weekly_count = models.PositiveIntegerField(default=0)
    monthly_count = models.PositiveIntegerField(default=0)
    
    # Context
    primary_category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_index=True
    )
    primary_location = models.ForeignKey(
        Location, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_index=True
    )
    
    # Status
    is_trending = models.BooleanField(default=False, db_index=True)
    is_suggested = models.BooleanField(default=True, db_index=True)
    
    # Timestamps
    first_searched = models.DateTimeField(auto_now_add=True)
    last_searched = models.DateTimeField(auto_now=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'popular_searches'
        ordering = ['-search_count']
        indexes = [
            models.Index(fields=['-search_count', 'is_suggested']),
            models.Index(fields=['-daily_count', 'is_trending']),
            models.Index(fields=['-weekly_count']),
            models.Index(fields=['primary_category', '-search_count']),
            models.Index(fields=['primary_location', '-search_count']),
        ]
    
    def __str__(self):
        return f"{self.query_text} ({self.search_count} searches)"


class SearchSuggestion(models.Model):
    """Search suggestions and autocomplete entries"""
    SUGGESTION_TYPES = [
        ('query', 'Query Suggestion'),
        ('category', 'Category'),
        ('location', 'Location'),
        ('company', 'Company'),
        ('skill', 'Skill'),
    ]
    
    # Suggestion content
    text = models.CharField(max_length=200, db_index=True)
    suggestion_type = models.CharField(max_length=20, choices=SUGGESTION_TYPES, db_index=True)
    
    # Ranking
    weight = models.PositiveIntegerField(default=0, db_index=True)  # Higher = more important
    usage_count = models.PositiveIntegerField(default=0, db_index=True)
    
    # Related data
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        db_index=True
    )
    location = models.ForeignKey(
        Location, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        db_index=True
    )
    
    # Settings
    is_active = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'search_suggestions'
        ordering = ['-weight', '-usage_count']
        indexes = [
            models.Index(fields=['text', 'suggestion_type']),
            models.Index(fields=['suggestion_type', 'is_active', '-weight']),
            models.Index(fields=['category', '-weight']),
            models.Index(fields=['location', '-weight']),
            models.Index(fields=['is_featured', '-weight']),
        ]
    
    def __str__(self):
        return f"{self.text} ({self.suggestion_type})"


class SavedSearch(models.Model):
    """User's saved search queries and filters"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='saved_searches',
        db_index=True
    )
    
    # Search details
    name = models.CharField(max_length=100)  # User-provided name
    query_text = models.CharField(max_length=500, blank=True)
    
    # Saved filters
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_index=True
    )
    location = models.ForeignKey(
        Location, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_index=True
    )
    job_type = models.CharField(max_length=20, blank=True)
    experience_level = models.CharField(max_length=20, blank=True)
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_remote = models.BooleanField(null=True, blank=True)
    
    # Additional filters (JSON for flexibility)
    additional_filters = models.JSONField(default=dict, blank=True)
    
    # Notifications
    email_alerts = models.BooleanField(default=False, db_index=True)
    alert_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
        ],
        default='daily'
    )
    last_alert_sent = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Usage tracking
    last_used = models.DateTimeField(null=True, blank=True, db_index=True)
    use_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'saved_searches'
        ordering = ['-last_used', '-created_at']
        indexes = [
            models.Index(fields=['user', '-last_used']),
            models.Index(fields=['email_alerts', 'alert_frequency']),
            models.Index(fields=['last_alert_sent']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.name}"
