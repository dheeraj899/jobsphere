from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Dashboard


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested relationships"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        ref_name = 'ActivityUserBasic'
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name']
        read_only_fields = ['id', 'username']
    
    def get_full_name(self, obj):
        """Return user's full name"""
        return f"{obj.first_name} {obj.last_name}".strip()


class DashboardSerializer(serializers.ModelSerializer):
    """Dashboard serializer with computed fields and validation"""
    user = UserBasicSerializer(read_only=True)
    total_job_applications = serializers.ReadOnlyField(source='total_applications')
    application_stats = serializers.SerializerMethodField()
    job_posting_stats = serializers.SerializerMethodField()
    activity_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = Dashboard
        fields = [
            'id', 'user', 'total_applications', 'active_applications',
            'jobs_posted', 'profile_views', 'pending_applications',
            'reviewed_applications', 'interview_applications',
            'accepted_applications', 'rejected_applications',
            'active_job_posts', 'total_job_applications_received',
            'jobs_filled', 'dashboard_layout', 'notification_preferences',
            'last_updated', 'stats_updated_at', 'total_job_applications',
            'application_stats', 'job_posting_stats', 'activity_summary'
        ]
        read_only_fields = [
            'id', 'user', 'last_updated', 'stats_updated_at',
            'total_job_applications', 'application_stats', 
            'job_posting_stats', 'activity_summary'
        ]
    
    def get_application_stats(self, obj):
        """Return application statistics summary"""
        total = obj.total_applications
        if total == 0:
            return {
                'total': 0,
                'pending_percentage': 0,
                'reviewed_percentage': 0,
                'interview_percentage': 0,
                'success_rate': 0,
                'rejection_rate': 0
            }
        
        return {
            'total': total,
            'pending_percentage': round((obj.pending_applications / total) * 100, 1),
            'reviewed_percentage': round((obj.reviewed_applications / total) * 100, 1),
            'interview_percentage': round((obj.interview_applications / total) * 100, 1),
            'success_rate': round((obj.accepted_applications / total) * 100, 1),
            'rejection_rate': round((obj.rejected_applications / total) * 100, 1)
        }
    
    def get_job_posting_stats(self, obj):
        """Return job posting statistics summary"""
        return {
            'active_posts': obj.active_job_posts,
            'total_applications_received': obj.total_job_applications_received,
            'jobs_successfully_filled': obj.jobs_filled,
            'avg_applications_per_job': (
                round(obj.total_job_applications_received / obj.jobs_posted, 1)
                if obj.jobs_posted > 0 else 0
            ),
            'fill_rate': (
                round((obj.jobs_filled / obj.jobs_posted) * 100, 1)
                if obj.jobs_posted > 0 else 0
            )
        }
    
    def get_activity_summary(self, obj):
        """Return overall activity summary"""
        return {
            'is_job_seeker': obj.total_applications > 0,
            'is_employer': obj.jobs_posted > 0,
            'is_active_job_seeker': obj.active_applications > 0,
            'is_active_employer': obj.active_job_posts > 0,
            'profile_visibility_score': min(obj.profile_views, 100),  # Cap at 100 for percentage
            'overall_activity_level': self._calculate_activity_level(obj)
        }
    
    def _calculate_activity_level(self, obj):
        """Calculate overall activity level (0-10 scale)"""
        score = 0
        
        # Job seeking activity (0-5 points)
        if obj.total_applications > 0:
            score += min(obj.total_applications / 10, 3)  # Up to 3 points for applications
            if obj.active_applications > 0:
                score += 1  # 1 point for having active applications
            if obj.accepted_applications > 0:
                score += 1  # 1 point for successful applications
        
        # Employer activity (0-5 points)
        if obj.jobs_posted > 0:
            score += min(obj.jobs_posted / 5, 2)  # Up to 2 points for job posts
            if obj.active_job_posts > 0:
                score += 1  # 1 point for active posts
            if obj.jobs_filled > 0:
                score += 1  # 1 point for successful fills
            if obj.total_job_applications_received > 0:
                score += 1  # 1 point for receiving applications
        
        return round(min(score, 10), 1)  # Cap at 10 and round to 1 decimal
    
    def validate_dashboard_layout(self, value):
        """Validate dashboard layout JSON structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Dashboard layout must be a valid JSON object.")
        
        # Check for required layout sections
        allowed_sections = [
            'widgets', 'layout', 'theme', 'sidebar_collapsed',
            'default_view', 'quick_actions', 'notifications_panel'
        ]
        
        for key in value.keys():
            if key not in allowed_sections:
                raise serializers.ValidationError(f"Invalid layout section: {key}")
        
        return value
    
    def validate_notification_preferences(self, value):
        """Validate notification preferences JSON structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Notification preferences must be a valid JSON object.")
        
        # Check for valid preference categories
        allowed_categories = [
            'email_notifications', 'push_notifications', 'sms_notifications',
            'job_alerts', 'application_updates', 'message_notifications',
            'system_notifications', 'marketing_notifications'
        ]
        
        for key in value.keys():
            if key not in allowed_categories:
                raise serializers.ValidationError(f"Invalid notification category: {key}")
            
            # Each category should be a boolean
            if not isinstance(value[key], bool):
                raise serializers.ValidationError(f"Notification preference '{key}' must be true or false.")
        
        return value


class DashboardUpdateSerializer(serializers.ModelSerializer):
    """Simplified serializer for dashboard updates"""
    
    class Meta:
        model = Dashboard
        fields = ['dashboard_layout', 'notification_preferences']
    
    def validate_dashboard_layout(self, value):
        """Validate dashboard layout JSON structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Dashboard layout must be a valid JSON object.")
        return value
    
    def validate_notification_preferences(self, value):
        """Validate notification preferences JSON structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Notification preferences must be a valid JSON object.")
        return value 