from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from .models import Category, SearchQuery, PopularSearch, SearchSuggestion, SavedSearch
from apps.map.models import Location


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested relationships"""
    class Meta:
        ref_name = 'SearchUserBasic'
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']
        read_only_fields = ['id', 'username']


class LocationBasicSerializer(serializers.ModelSerializer):
    """Basic location serializer for nested relationships"""
    class Meta:
        model = Location
        fields = ['id', 'name', 'city', 'state_province', 'country']
        read_only_fields = ['id']


class CategorySerializer(serializers.ModelSerializer):
    """Category serializer with hierarchy support and validation"""
    parent_name = serializers.SerializerMethodField()
    subcategories_count = serializers.SerializerMethodField()
    full_path = serializers.ReadOnlyField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'parent', 'parent_name',
            'level', 'icon', 'color', 'order', 'is_active', 'job_count',
            'created_at', 'updated_at', 'subcategories_count', 'full_path'
        ]
        read_only_fields = ['id', 'slug', 'level', 'job_count', 'created_at', 'updated_at', 'full_path']
    
    def get_parent_name(self, obj):
        """Return parent category name"""
        return obj.parent.name if obj.parent else None
    
    def get_subcategories_count(self, obj):
        """Return count of active subcategories"""
        return obj.subcategories.filter(is_active=True).count()
    
    def validate_name(self, value):
        """Validate category name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Category name cannot be empty.")
        if len(value) > 100:
            raise serializers.ValidationError("Category name cannot be longer than 100 characters.")
        return value.strip()
    
    def validate_color(self, value):
        """Validate color hex code"""
        if value and not value.startswith('#'):
            raise serializers.ValidationError("Color must be a valid hex code starting with #.")
        if value and len(value) != 7:
            raise serializers.ValidationError("Color must be a 7-character hex code (e.g., #FF0000).")
        return value
    
    def validate_order(self, value):
        """Validate order value"""
        if value < 0:
            raise serializers.ValidationError("Order must be a positive integer.")
        return value
    
    def create(self, validated_data):
        """Create category with auto-generated slug"""
        if not validated_data.get('slug'):
            validated_data['slug'] = slugify(validated_data['name'])
        
        # Set level based on parent
        if validated_data.get('parent'):
            validated_data['level'] = validated_data['parent'].level + 1
        else:
            validated_data['level'] = 0
        
        return super().create(validated_data)


class CategoryListSerializer(serializers.ModelSerializer):
    """Simplified serializer for category lists"""
    subcategories_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'color', 'level', 'job_count', 'subcategories_count']
        read_only_fields = ['id', 'slug', 'level', 'job_count']
    
    def get_subcategories_count(self, obj):
        """Return count of active subcategories"""
        return obj.subcategories.filter(is_active=True).count()


class SearchQuerySerializer(serializers.ModelSerializer):
    """Search query serializer with analytics data"""
    user = UserBasicSerializer(read_only=True)
    category = CategoryListSerializer(read_only=True)
    location = LocationBasicSerializer(read_only=True)
    search_context = serializers.SerializerMethodField()
    performance_metrics = serializers.SerializerMethodField()
    
    class Meta:
        model = SearchQuery
        fields = [
            'id', 'query_text', 'normalized_query', 'user', 'session_id',
            'ip_address', 'search_type', 'category', 'location',
            'job_type', 'experience_level', 'salary_min', 'salary_max',
            'is_remote', 'results_count', 'has_results',
            'clicked_result_position', 'clicked_result_id', 'time_spent',
            'user_agent', 'referrer', 'searched_at', 'search_context',
            'performance_metrics'
        ]
        read_only_fields = [
            'id', 'user', 'normalized_query', 'ip_address', 'user_agent',
            'searched_at', 'search_context', 'performance_metrics'
        ]
    
    def get_search_context(self, obj):
        """Return search context summary"""
        return {
            'has_user': obj.user is not None,
            'has_category_filter': obj.category is not None,
            'has_location_filter': obj.location is not None,
            'has_salary_filter': obj.salary_min is not None or obj.salary_max is not None,
            'has_remote_filter': obj.is_remote is not None,
            'total_filters_applied': sum([
                bool(obj.category),
                bool(obj.location),
                bool(obj.job_type),
                bool(obj.experience_level),
                bool(obj.salary_min or obj.salary_max),
                bool(obj.is_remote is not None)
            ])
        }
    
    def get_performance_metrics(self, obj):
        """Return search performance metrics"""
        return {
            'found_results': obj.has_results,
            'results_count': obj.results_count,
            'user_engaged': obj.clicked_result_position is not None,
            'time_spent_seconds': obj.time_spent.total_seconds() if obj.time_spent else None,
            'clicked_position': obj.clicked_result_position
        }


class PopularSearchSerializer(serializers.ModelSerializer):
    """Popular search serializer with trending data"""
    primary_category = CategoryListSerializer(read_only=True)
    primary_location = LocationBasicSerializer(read_only=True)
    trend_data = serializers.SerializerMethodField()
    growth_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = PopularSearch
        fields = [
            'id', 'query_text', 'search_count', 'daily_count',
            'weekly_count', 'monthly_count', 'primary_category',
            'primary_location', 'is_trending', 'is_suggested',
            'first_searched', 'last_searched', 'updated_at',
            'trend_data', 'growth_rate'
        ]
        read_only_fields = [
            'id', 'search_count', 'daily_count', 'weekly_count',
            'monthly_count', 'first_searched', 'last_searched',
            'updated_at', 'trend_data', 'growth_rate'
        ]
    
    def get_trend_data(self, obj):
        """Return trending analysis"""
        return {
            'daily_percentage': round((obj.daily_count / max(obj.search_count, 1)) * 100, 1),
            'weekly_percentage': round((obj.weekly_count / max(obj.search_count, 1)) * 100, 1),
            'monthly_percentage': round((obj.monthly_count / max(obj.search_count, 1)) * 100, 1),
            'is_trending_up': obj.is_trending,
            'search_frequency': self._calculate_frequency(obj)
        }
    
    def get_growth_rate(self, obj):
        """Calculate growth rate based on recent activity"""
        if obj.weekly_count == 0:
            return 0
        
        # Simple growth rate calculation (daily vs weekly average)
        weekly_avg = obj.weekly_count / 7
        if weekly_avg == 0:
            return 0
        
        return round(((obj.daily_count - weekly_avg) / weekly_avg) * 100, 1)
    
    def _calculate_frequency(self, obj):
        """Calculate search frequency category"""
        if obj.daily_count >= 50:
            return 'very_high'
        elif obj.daily_count >= 20:
            return 'high'
        elif obj.daily_count >= 5:
            return 'medium'
        elif obj.daily_count >= 1:
            return 'low'
        else:
            return 'rare'


class SearchSuggestionSerializer(serializers.ModelSerializer):
    """Search suggestion serializer with ranking data"""
    category = CategoryListSerializer(read_only=True)
    location = LocationBasicSerializer(read_only=True)
    suggestion_context = serializers.SerializerMethodField()
    
    class Meta:
        model = SearchSuggestion
        fields = [
            'id', 'text', 'suggestion_type', 'weight', 'usage_count',
            'category', 'location', 'is_active', 'is_featured',
            'metadata', 'created_at', 'updated_at', 'suggestion_context'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at', 'suggestion_context']
    
    def get_suggestion_context(self, obj):
        """Return suggestion context information"""
        return {
            'has_category_context': obj.category is not None,
            'has_location_context': obj.location is not None,
            'popularity_score': min(obj.usage_count / 100, 1.0),  # Normalized 0-1 score
            'weight_category': 'high' if obj.weight >= 80 else 'medium' if obj.weight >= 40 else 'low'
        }
    
    def validate_text(self, value):
        """Validate suggestion text"""
        if not value or not value.strip():
            raise serializers.ValidationError("Suggestion text cannot be empty.")
        if len(value) > 200:
            raise serializers.ValidationError("Suggestion text cannot be longer than 200 characters.")
        return value.strip()
    
    def validate_weight(self, value):
        """Validate weight value"""
        if value < 0 or value > 100:
            raise serializers.ValidationError("Weight must be between 0 and 100.")
        return value
    
    def validate_suggestion_type(self, value):
        """Validate suggestion type"""
        valid_types = dict(SearchSuggestion.SUGGESTION_TYPES).keys()
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid suggestion type. Must be one of: {', '.join(valid_types)}")
        return value


class SavedSearchSerializer(serializers.ModelSerializer):
    """Saved search serializer with alert configuration"""
    user = UserBasicSerializer(read_only=True)
    category = CategoryListSerializer(read_only=True)
    location = LocationBasicSerializer(read_only=True)
    search_summary = serializers.SerializerMethodField()
    alert_status = serializers.SerializerMethodField()
    usage_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = SavedSearch
        fields = [
            'id', 'user', 'name', 'query_text', 'category', 'location',
            'job_type', 'experience_level', 'salary_min', 'salary_max',
            'is_remote', 'additional_filters', 'email_alerts',
            'alert_frequency', 'last_alert_sent', 'last_used',
            'use_count', 'created_at', 'updated_at', 'search_summary',
            'alert_status', 'usage_stats'
        ]
        read_only_fields = [
            'id', 'user', 'last_alert_sent', 'last_used', 'use_count',
            'created_at', 'updated_at', 'search_summary', 'alert_status', 'usage_stats'
        ]
    
    def get_search_summary(self, obj):
        """Return search configuration summary"""
        filters_count = sum([
            bool(obj.category),
            bool(obj.location),
            bool(obj.job_type),
            bool(obj.experience_level),
            bool(obj.salary_min or obj.salary_max),
            bool(obj.is_remote is not None),
            bool(obj.additional_filters)
        ])
        
        return {
            'has_query': bool(obj.query_text),
            'total_filters': filters_count,
            'has_salary_filter': bool(obj.salary_min or obj.salary_max),
            'is_remote_specific': obj.is_remote is not None,
            'complexity_level': 'high' if filters_count >= 4 else 'medium' if filters_count >= 2 else 'simple'
        }
    
    def get_alert_status(self, obj):
        """Return alert configuration status"""
        if not obj.email_alerts:
            return {
                'enabled': False,
                'frequency': None,
                'last_sent': None,
                'next_due': None
            }
        
        next_due = None
        if obj.last_alert_sent:
            if obj.alert_frequency == 'daily':
                next_due = obj.last_alert_sent + timezone.timedelta(days=1)
            elif obj.alert_frequency == 'weekly':
                next_due = obj.last_alert_sent + timezone.timedelta(weeks=1)
        
        return {
            'enabled': True,
            'frequency': obj.alert_frequency,
            'last_sent': obj.last_alert_sent,
            'next_due': next_due,
            'is_overdue': next_due and timezone.now() > next_due if next_due else False
        }
    
    def get_usage_stats(self, obj):
        """Return usage statistics"""
        return {
            'total_uses': obj.use_count,
            'created_days_ago': (timezone.now() - obj.created_at).days,
            'last_used_days_ago': (timezone.now() - obj.last_used).days if obj.last_used else None,
            'is_frequently_used': obj.use_count >= 10,
            'is_recently_used': obj.last_used and (timezone.now() - obj.last_used).days <= 7 if obj.last_used else False
        }
    
    def validate_name(self, value):
        """Validate saved search name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Search name cannot be empty.")
        if len(value) > 100:
            raise serializers.ValidationError("Search name cannot be longer than 100 characters.")
        return value.strip()
    
    def validate_alert_frequency(self, value):
        """Validate alert frequency"""
        valid_frequencies = ['immediate', 'daily', 'weekly']
        if value not in valid_frequencies:
            raise serializers.ValidationError(f"Invalid alert frequency. Must be one of: {', '.join(valid_frequencies)}")
        return value
    
    def validate_additional_filters(self, value):
        """Validate additional filters JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Additional filters must be a valid JSON object.")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # Validate salary range
        salary_min = data.get('salary_min')
        salary_max = data.get('salary_max')
        
        if salary_min is not None and salary_max is not None:
            if salary_min >= salary_max:
                raise serializers.ValidationError("Minimum salary must be less than maximum salary.")
            if salary_min < 0:
                raise serializers.ValidationError("Salary values must be positive.")
        
        return data 