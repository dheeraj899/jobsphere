from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
from .models import Job, JobApplication, JobView, SavedJob
from apps.map.models import Location


class LocationSerializer(serializers.ModelSerializer):
    """Basic location serializer for nested relationships"""
    full_address = serializers.ReadOnlyField()
    
    class Meta:
        ref_name = 'JobsLocationSerializer'
        model = Location
        fields = [
            'id', 'name', 'city', 'state_province', 'country',
            'latitude', 'longitude', 'full_address'
        ]
        read_only_fields = ['id', 'full_address']


class JobSerializer(serializers.ModelSerializer):
    """Job serializer with validation and computed fields"""
    posted_by = serializers.StringRelatedField(read_only=True)
    location = LocationSerializer(read_only=True)
    location_id = serializers.IntegerField(write_only=True)
    salary_range = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    time_since_posted = serializers.SerializerMethodField()
    application_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'description', 'requirements', 'benefits',
            'job_type', 'experience_level', 'category', 'skills_required',
            'salary_min', 'salary_max', 'salary_currency', 'salary_type',
            'location', 'location_id', 'is_remote', 'remote_type',
            'posted_by', 'status', 'application_deadline', 'max_applications',
            'application_email', 'application_url', 'slug', 'meta_description',
            'view_count', 'application_count', 'created_at', 'updated_at',
            'published_at', 'salary_range', 'is_expired', 'time_since_posted'
        ]
        read_only_fields = [
            'id', 'posted_by', 'slug', 'view_count', 'application_count',
            'created_at', 'updated_at', 'salary_range', 'is_expired'
        ]
    
    def get_time_since_posted(self, obj):
        """Return human-readable time since posted"""
        if obj.published_at:
            time_diff = timezone.now() - obj.published_at
            days = time_diff.days
            
            if days == 0:
                hours = time_diff.seconds // 3600
                if hours == 0:
                    minutes = time_diff.seconds // 60
                    return f"{minutes}m ago"
                return f"{hours}h ago"
            elif days == 1:
                return "1 day ago"
            elif days < 7:
                return f"{days} days ago"
            elif days < 30:
                weeks = days // 7
                return f"{weeks}w ago"
            else:
                months = days // 30
                return f"{months}mo ago"
        return None
    
    def validate_title(self, value):
        """Validate job title"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Job title must be at least 5 characters long.")
        return value.strip()
    
    def validate_description(self, value):
        """Validate job description"""
        if len(value.strip()) < 100:
            raise serializers.ValidationError("Job description must be at least 100 characters long.")
        return value.strip()
    
    def validate_salary_min(self, value):
        """Validate minimum salary"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Minimum salary cannot be negative.")
        return value
    
    def validate_salary_max(self, value):
        """Validate maximum salary"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Maximum salary cannot be negative.")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        salary_min = data.get('salary_min')
        salary_max = data.get('salary_max')
        
        if salary_min and salary_max and salary_min > salary_max:
            raise serializers.ValidationError("Minimum salary cannot be greater than maximum salary.")
        
        application_deadline = data.get('application_deadline')
        if application_deadline and application_deadline <= timezone.now():
            raise serializers.ValidationError("Application deadline must be in the future.")
        
        return data
    
    def create(self, validated_data):
        """Create job with auto-generated slug"""
        if not validated_data.get('slug'):
            base_slug = slugify(f"{validated_data['title']}-{validated_data['company']}")
            counter = 1
            slug = base_slug
            while Job.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            validated_data['slug'] = slug
        
        # Set posted_by from request user
        validated_data['posted_by'] = self.context['request'].user
        
        return super().create(validated_data)


class JobListSerializer(serializers.ModelSerializer):
    """Simplified job serializer for list views"""
    posted_by = serializers.StringRelatedField(read_only=True)
    location = LocationSerializer(read_only=True)
    salary_range = serializers.ReadOnlyField()
    time_since_posted = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'company', 'job_type', 'experience_level', 'category',
            'salary_range', 'location', 'is_remote', 'remote_type', 'posted_by',
            'status', 'view_count', 'application_count', 'published_at', 'time_since_posted'
        ]
    
    def get_time_since_posted(self, obj):
        """Return human-readable time since posted"""
        if obj.published_at:
            time_diff = timezone.now() - obj.published_at
            days = time_diff.days
            
            if days == 0:
                return "Today"
            elif days == 1:
                return "Yesterday"
            elif days < 7:
                return f"{days} days ago"
            elif days < 30:
                weeks = days // 7
                return f"{weeks} week{'s' if weeks > 1 else ''} ago"
            else:
                months = days // 30
                return f"{months} month{'s' if months > 1 else ''} ago"
        return None


class JobApplicationSerializer(serializers.ModelSerializer):
    """Job application serializer with validation"""
    applicant = serializers.StringRelatedField(read_only=True)
    job = JobListSerializer(read_only=True)
    job_id = serializers.IntegerField(write_only=True)
    time_since_applied = serializers.SerializerMethodField()
    
    class Meta:
        model = JobApplication
        fields = [
            'id', 'job', 'job_id', 'applicant', 'cover_letter', 'resume_file',
            'portfolio_url', 'status', 'notes', 'last_contact_date',
            'interview_scheduled_at', 'source', 'applied_at', 'updated_at',
            'time_since_applied'
        ]
        read_only_fields = [
            'id', 'applicant', 'notes', 'last_contact_date', 'interview_scheduled_at',
            'applied_at', 'updated_at'
        ]
    
    def get_time_since_applied(self, obj):
        """Return human-readable time since applied"""
        time_diff = timezone.now() - obj.applied_at
        days = time_diff.days
        
        if days == 0:
            hours = time_diff.seconds // 3600
            if hours == 0:
                return "Just now"
            return f"{hours}h ago"
        elif days == 1:
            return "Yesterday"
        elif days < 7:
            return f"{days} days ago"
        else:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    
    def validate_cover_letter(self, value):
        """Validate cover letter"""
        if value and len(value.strip()) < 50:
            raise serializers.ValidationError("Cover letter should be at least 50 characters long.")
        return value.strip() if value else value
    
    def validate_job_id(self, value):
        """Validate job exists and is active"""
        try:
            job = Job.objects.get(id=value)
            if job.status != 'active':
                raise serializers.ValidationError("Cannot apply to inactive jobs.")
            if job.application_deadline and job.application_deadline <= timezone.now():
                raise serializers.ValidationError("Application deadline has passed.")
        except Job.DoesNotExist:
            raise serializers.ValidationError("Job does not exist.")
        return value
    
    def create(self, validated_data):
        """Create application with user from request"""
        validated_data['applicant'] = self.context['request'].user
        
        # Check if user already applied
        job_id = validated_data['job_id']
        user = validated_data['applicant']
        
        if JobApplication.objects.filter(job_id=job_id, applicant=user).exists():
            raise serializers.ValidationError("You have already applied to this job.")
        
        return super().create(validated_data)


class JobViewSerializer(serializers.ModelSerializer):
    """Job view tracking serializer"""
    user = serializers.StringRelatedField(read_only=True)
    job = JobListSerializer(read_only=True)
    
    class Meta:
        model = JobView
        fields = [
            'id', 'job', 'user', 'ip_address', 'user_agent', 'referrer',
            'source', 'viewed_at'
        ]
        read_only_fields = ['id', 'user', 'viewed_at']


class SavedJobSerializer(serializers.ModelSerializer):
    """Saved job serializer"""
    user = serializers.StringRelatedField(read_only=True)
    job = JobListSerializer(read_only=True)
    job_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = SavedJob
        fields = [
            'id', 'user', 'job', 'job_id', 'notes', 'saved_at'
        ]
        read_only_fields = ['id', 'user', 'saved_at']
    
    def validate_job_id(self, value):
        """Validate job exists"""
        try:
            Job.objects.get(id=value)
        except Job.DoesNotExist:
            raise serializers.ValidationError("Job does not exist.")
        return value
    
    def create(self, validated_data):
        """Create saved job with user from request"""
        validated_data['user'] = self.context['request'].user
        
        # Check if job is already saved
        job_id = validated_data['job_id']
        user = validated_data['user']
        
        if SavedJob.objects.filter(job_id=job_id, user=user).exists():
            raise serializers.ValidationError("You have already saved this job.")
        
        return super().create(validated_data) 

# Alias serializers for create operations
JobCreateSerializer = JobSerializer
JobApplicationCreateSerializer = JobApplicationSerializer 