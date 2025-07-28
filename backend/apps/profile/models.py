from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.indexes import GinIndex


class UserProfile(models.Model):
    """Extended user profile with additional information"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile',
        db_index=True
    )
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)
    
    # Profile visibility and status
    is_active = models.BooleanField(default=True, db_index=True)
    is_verified = models.BooleanField(default=False, db_index=True)
    is_employer = models.BooleanField(default=False, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profiles'
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['is_active', 'is_verified']),
            models.Index(fields=['location']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class Experience(models.Model):
    """User work experience entries"""
    EXPERIENCE_TYPES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('freelance', 'Freelance'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='experiences',
        db_index=True
    )
    title = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    location = models.CharField(max_length=100, blank=True)
    experience_type = models.CharField(max_length=20, choices=EXPERIENCE_TYPES, db_index=True)
    description = models.TextField(blank=True)
    
    # Date fields
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # null for current positions
    is_current = models.BooleanField(default=False, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_experiences'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['user', '-start_date']),
            models.Index(fields=['experience_type']),
            models.Index(fields=['is_current']),
        ]
    
    def __str__(self):
        return f"{self.title} at {self.company}"


class About(models.Model):
    """User's about section with detailed information"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='about',
        db_index=True
    )
    summary = models.TextField(max_length=2000, blank=True)
    skills = models.TextField(blank=True, help_text="Comma-separated skills")
    interests = models.TextField(blank=True, help_text="Comma-separated interests")
    languages = models.TextField(blank=True, help_text="Comma-separated languages")
    
    # Professional details
    years_of_experience = models.PositiveIntegerField(null=True, blank=True)
    current_salary_range = models.CharField(max_length=50, blank=True)
    expected_salary_range = models.CharField(max_length=50, blank=True)
    availability = models.CharField(max_length=50, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_about'
    
    def __str__(self):
        return f"{self.user.username}'s About"


class Contact(models.Model):
    """User contact information with JSON field for flexible data"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='contact',
        db_index=True
    )
    
    # Basic contact info
    primary_email = models.EmailField()
    secondary_email = models.EmailField(blank=True)
    primary_phone = models.CharField(max_length=20, blank=True)
    secondary_phone = models.CharField(max_length=20, blank=True)
    
    # Address
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    
    # Flexible JSON field for additional contact methods
    additional_contacts = models.JSONField(
        default=dict, 
        blank=True,
        help_text="JSON field for additional contact methods like social media, messaging apps, etc."
    )
    
    # Privacy settings
    show_email = models.BooleanField(default=True)
    show_phone = models.BooleanField(default=True)
    show_address = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_contacts'
        indexes = [
            # GIN index for JSON field queries
            GinIndex(fields=['additional_contacts']),
            models.Index(fields=['city', 'state']),
            models.Index(fields=['country']),
        ]
    
    def __str__(self):
        return f"{self.user.username}'s Contact Info" 