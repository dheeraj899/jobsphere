from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from apps.map.models import Location


class Job(models.Model):
    """Job postings with full-text search capabilities"""
    JOB_TYPES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('internship', 'Internship'),
        ('freelance', 'Freelance'),
        ('temporary', 'Temporary'),
    ]
    
    EXPERIENCE_LEVELS = [
        ('entry', 'Entry Level'),
        ('junior', 'Junior'),
        ('mid', 'Mid Level'),
        ('senior', 'Senior'),
        ('lead', 'Lead'),
        ('executive', 'Executive'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('filled', 'Filled'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic job information
    title = models.CharField(max_length=200, db_index=True)
    company = models.CharField(max_length=100, db_index=True)
    description = models.TextField(help_text="Full job description")
    requirements = models.TextField(blank=True, help_text="Job requirements and qualifications")
    benefits = models.TextField(blank=True, help_text="Job benefits and perks")
    
    # Job classification
    job_type = models.CharField(max_length=20, choices=JOB_TYPES, db_index=True)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVELS, db_index=True)
    category = models.CharField(max_length=100, db_index=True)  # e.g., "Technology", "Marketing"
    skills_required = models.TextField(blank=True, help_text="Comma-separated skills")
    
    # Compensation
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default='USD')
    salary_type = models.CharField(
        max_length=20,
        choices=[
            ('hourly', 'Hourly'),
            ('monthly', 'Monthly'),
            ('yearly', 'Yearly'),
        ],
        default='yearly',
        db_index=True
    )
    
    # Location
    location = models.ForeignKey(
        Location, 
        on_delete=models.CASCADE, 
        related_name='jobs',
        db_index=True
    )
    is_remote = models.BooleanField(default=False, db_index=True)
    remote_type = models.CharField(
        max_length=20,
        choices=[
            ('no', 'Not Remote'),
            ('partial', 'Partially Remote'),
            ('full', 'Fully Remote'),
        ],
        default='no',
        db_index=True
    )
    
    # Posting details
    posted_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='posted_jobs',
        db_index=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    
    # Application settings
    application_deadline = models.DateTimeField(null=True, blank=True, db_index=True)
    max_applications = models.PositiveIntegerField(null=True, blank=True)
    application_email = models.EmailField(blank=True)
    application_url = models.URLField(blank=True)
    
    # SEO and metadata
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    meta_description = models.CharField(max_length=160, blank=True)
    
    # Full-text search vector
    search_vector = SearchVectorField(null=True, blank=True)
    
    # Analytics
    view_count = models.PositiveIntegerField(default=0, db_index=True)
    application_count = models.PositiveIntegerField(default=0, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    class Meta:
        db_table = 'jobs'
        ordering = ['-created_at']
        indexes = [
            # B-tree indexes for common queries
            models.Index(fields=['status', 'job_type']),
            models.Index(fields=['category', 'experience_level']),
            models.Index(fields=['posted_by', 'status']),
            models.Index(fields=['location', 'is_remote']),
            models.Index(fields=['published_at', 'status']),
            models.Index(fields=['application_deadline']),
            models.Index(fields=['salary_min', 'salary_max']),
            
            # GIN index for full-text search
            GinIndex(fields=['search_vector']),
        ]
    
    def __str__(self):
        return f"{self.title} at {self.company}"
    
    @property
    def is_expired(self):
        """Check if job application deadline has passed"""
        if self.application_deadline:
            from django.utils import timezone
            return timezone.now() > self.application_deadline
        return False
    
    @property
    def salary_range(self):
        """Return formatted salary range"""
        if self.salary_min and self.salary_max:
            return f"{self.salary_currency} {self.salary_min:,.0f} - {self.salary_max:,.0f} {self.salary_type}"
        elif self.salary_min:
            return f"{self.salary_currency} {self.salary_min:,.0f}+ {self.salary_type}"
        return "Salary not specified"


class JobApplication(models.Model):
    """Job applications from users"""
    APPLICATION_STATUS = [
        ('pending', 'Pending'),
        ('reviewed', 'Reviewed'),
        ('shortlisted', 'Shortlisted'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('interview_completed', 'Interview Completed'),
        ('offer_made', 'Offer Made'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
    ]
    
    # Core relationships
    job = models.ForeignKey(
        Job, 
        on_delete=models.CASCADE, 
        related_name='applications',
        db_index=True
    )
    applicant = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='job_applications',
        db_index=True
    )
    
    # Application content
    cover_letter = models.TextField(blank=True)
    resume_file = models.FileField(upload_to='resumes/', blank=True)
    portfolio_url = models.URLField(blank=True)
    
    # Status tracking
    status = models.CharField(max_length=30, choices=APPLICATION_STATUS, default='pending', db_index=True)
    notes = models.TextField(blank=True, help_text="Internal notes from employer")
    
    # Communication
    last_contact_date = models.DateTimeField(null=True, blank=True, db_index=True)
    interview_scheduled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Metadata
    source = models.CharField(
        max_length=50,
        choices=[
            ('website', 'Website'),
            ('mobile_app', 'Mobile App'),
            ('external', 'External Site'),
            ('referral', 'Referral'),
        ],
        default='website',
        db_index=True
    )
    
    # Timestamps
    applied_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'job_applications'
        unique_together = [['job', 'applicant']]  # One application per job per user
        ordering = ['-applied_at']
        indexes = [
            models.Index(fields=['job', 'status']),
            models.Index(fields=['applicant', 'status']),
            models.Index(fields=['status', '-applied_at']),
            models.Index(fields=['job', '-applied_at']),
            models.Index(fields=['interview_scheduled_at']),
            models.Index(fields=['last_contact_date']),
        ]
    
    def __str__(self):
        return f"{self.applicant.username} applied to {self.job.title}"


class JobView(models.Model):
    """Track job views for analytics"""
    job = models.ForeignKey(
        Job, 
        on_delete=models.CASCADE, 
        related_name='job_views',
        db_index=True
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_index=True
    )
    ip_address = models.GenericIPAddressField(db_index=True)
    user_agent = models.TextField(blank=True)
    
    # View context
    referrer = models.URLField(blank=True)
    source = models.CharField(
        max_length=50,
        choices=[
            ('search', 'Search Results'),
            ('browse', 'Browse/Category'),
            ('map', 'Map View'),
            ('direct', 'Direct Link'),
            ('social', 'Social Media'),
        ],
        blank=True,
        db_index=True
    )
    
    # Timestamps
    viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'job_views'
        indexes = [
            models.Index(fields=['job', '-viewed_at']),
            models.Index(fields=['user', '-viewed_at']),
            models.Index(fields=['ip_address', '-viewed_at']),
            models.Index(fields=['source', '-viewed_at']),
        ]
    
    def __str__(self):
        user_info = self.user.username if self.user else self.ip_address
        return f"{user_info} viewed {self.job.title}"


class SavedJob(models.Model):
    """Jobs saved by users for later"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='saved_jobs',
        db_index=True
    )
    job = models.ForeignKey(
        Job, 
        on_delete=models.CASCADE, 
        related_name='saved_by_users',
        db_index=True
    )
    notes = models.TextField(blank=True, help_text="Personal notes about this job")
    
    # Timestamps
    saved_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'saved_jobs'
        unique_together = [['user', 'job']]
        ordering = ['-saved_at']
        indexes = [
            models.Index(fields=['user', '-saved_at']),
            models.Index(fields=['job', '-saved_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} saved {self.job.title}"
