from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile, Experience, About, Contact


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested relationships"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id', 'username']


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile serializer with validation and permissions"""
    user = UserSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'avatar', 'bio', 'location', 'phone', 'website',
            'linkedin', 'github', 'is_active', 'is_verified', 'is_employer',
            'created_at', 'updated_at', 'full_name'
        ]
        read_only_fields = ['id', 'user', 'is_verified', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        """Return user's full name"""
        return f"{obj.user.first_name} {obj.user.last_name}".strip()
    
    def validate_phone(self, value):
        """Validate phone number format"""
        if value and not value.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise serializers.ValidationError("Phone number must contain only digits, spaces, hyphens, and plus sign.")
        return value
    
    def validate_website(self, value):
        """Validate website URL"""
        if value and not (value.startswith('http://') or value.startswith('https://')):
            raise serializers.ValidationError("Website URL must start with http:// or https://")
        return value


class ExperienceSerializer(serializers.ModelSerializer):
    """Experience serializer with validation for date consistency"""
    duration_months = serializers.SerializerMethodField()
    is_ongoing = serializers.SerializerMethodField()
    
    class Meta:
        model = Experience
        fields = [
            'id', 'title', 'company', 'location', 'experience_type', 'description',
            'start_date', 'end_date', 'is_current', 'created_at', 'updated_at',
            'duration_months', 'is_ongoing'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_duration_months(self, obj):
        """Calculate duration in months"""
        if obj.is_current:
            from django.utils import timezone
            end_date = timezone.now().date()
        else:
            end_date = obj.end_date
        
        if end_date and obj.start_date:
            months = (end_date.year - obj.start_date.year) * 12 + (end_date.month - obj.start_date.month)
            return max(1, months)  # At least 1 month
        return None
    
    def get_is_ongoing(self, obj):
        """Return if this is current position"""
        return obj.is_current
    
    def validate(self, data):
        """Validate date consistency"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        is_current = data.get('is_current', False)
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("Start date cannot be after end date.")
        
        if is_current and end_date:
            raise serializers.ValidationError("Current positions should not have an end date.")
        
        if not is_current and not end_date:
            raise serializers.ValidationError("Non-current positions must have an end date.")
        
        return data


class AboutSerializer(serializers.ModelSerializer):
    """About section serializer with skills parsing"""
    skills_list = serializers.SerializerMethodField()
    interests_list = serializers.SerializerMethodField()
    languages_list = serializers.SerializerMethodField()
    
    class Meta:
        model = About
        fields = [
            'id', 'summary', 'skills', 'interests', 'languages',
            'years_of_experience', 'current_salary_range', 'expected_salary_range',
            'availability', 'created_at', 'updated_at', 'skills_list',
            'interests_list', 'languages_list'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_skills_list(self, obj):
        """Return skills as a list"""
        if obj.skills:
            return [skill.strip() for skill in obj.skills.split(',') if skill.strip()]
        return []
    
    def get_interests_list(self, obj):
        """Return interests as a list"""
        if obj.interests:
            return [interest.strip() for interest in obj.interests.split(',') if interest.strip()]
        return []
    
    def get_languages_list(self, obj):
        """Return languages as a list"""
        if obj.languages:
            return [language.strip() for language in obj.languages.split(',') if language.strip()]
        return []
    
    def validate_years_of_experience(self, value):
        """Validate years of experience"""
        if value is not None and (value < 0 or value > 50):
            raise serializers.ValidationError("Years of experience must be between 0 and 50.")
        return value
    
    def validate_summary(self, value):
        """Validate summary length and content"""
        if value and len(value.strip()) < 50:
            raise serializers.ValidationError("Summary should be at least 50 characters long.")
        return value


class ContactSerializer(serializers.ModelSerializer):
    """Contact serializer with privacy controls"""
    class Meta:
        model = Contact
        fields = [
            'id', 'primary_email', 'secondary_email', 'primary_phone', 'secondary_phone',
            'address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country',
            'additional_contacts', 'show_email', 'show_phone', 'show_address',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_primary_email(self, value):
        """Validate primary email is provided"""
        if not value:
            raise serializers.ValidationError("Primary email is required.")
        return value
    
    def validate_additional_contacts(self, value):
        """Validate additional contacts JSON structure"""
        if value and not isinstance(value, dict):
            raise serializers.ValidationError("Additional contacts must be a valid JSON object.")
        
        # Validate structure
        allowed_keys = ['twitter', 'facebook', 'instagram', 'telegram', 'whatsapp', 'skype', 'discord', 'other']
        if value:
            for key in value.keys():
                if key not in allowed_keys:
                    raise serializers.ValidationError(f"'{key}' is not an allowed contact method.")
        
        return value
    
    def to_representation(self, instance):
        """Apply privacy controls to representation"""
        data = super().to_representation(instance)
        
        # Apply privacy settings
        if not instance.show_email:
            data.pop('primary_email', None)
            data.pop('secondary_email', None)
        
        if not instance.show_phone:
            data.pop('primary_phone', None)
            data.pop('secondary_phone', None)
        
        if not instance.show_address:
            data.pop('address_line1', None)
            data.pop('address_line2', None)
            data.pop('city', None)
            data.pop('state', None)
            data.pop('postal_code', None)
            data.pop('country', None)
        
        return data


class UserProfileDetailSerializer(serializers.ModelSerializer):
    """Detailed user profile serializer with nested relationships"""
    user = UserSerializer(read_only=True)
    experiences = ExperienceSerializer(source='user.experiences', many=True, read_only=True)
    about = AboutSerializer(source='user.about', read_only=True)
    contact = ContactSerializer(source='user.contact', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'avatar', 'bio', 'location', 'phone', 'website',
            'linkedin', 'github', 'is_active', 'is_verified', 'is_employer',
            'created_at', 'updated_at', 'experiences', 'about', 'contact'
        ]
        read_only_fields = ['id', 'user', 'is_verified', 'created_at', 'updated_at'] 