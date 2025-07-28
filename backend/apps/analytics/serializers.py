from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import ResponseTime


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested relationships"""
    class Meta:
        ref_name = 'AnalyticsUserBasic'
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']
        read_only_fields = ['id', 'username']


class ResponseTimeSerializer(serializers.ModelSerializer):
    """Response time serializer with performance analytics"""
    user = UserBasicSerializer(read_only=True)
    performance_grade = serializers.ReadOnlyField()
    is_slow = serializers.ReadOnlyField()
    performance_metrics = serializers.SerializerMethodField()
    request_context = serializers.SerializerMethodField()
    
    class Meta:
        model = ResponseTime
        fields = [
            'id', 'endpoint', 'http_method', 'endpoint_category',
            'response_time_ms', 'db_query_time_ms', 'db_query_count',
            'cache_hit', 'status_code', 'response_size_bytes',
            'user', 'ip_address', 'user_agent', 'server_name',
            'process_id', 'has_error', 'error_type', 'error_message',
            'timestamp', 'performance_grade', 'is_slow',
            'performance_metrics', 'request_context'
        ]
        read_only_fields = [
            'id', 'user', 'timestamp', 'performance_grade', 'is_slow',
            'performance_metrics', 'request_context'
        ]
    
    def get_performance_metrics(self, obj):
        """Return detailed performance analysis"""
        # Calculate various performance metrics
        db_percentage = (
            round((obj.db_query_time_ms / obj.response_time_ms) * 100, 1)
            if obj.db_query_time_ms and obj.response_time_ms > 0 else 0
        )
        
        return {
            'total_response_time': obj.response_time_ms,
            'database_time_percentage': db_percentage,
            'application_time_ms': (
                obj.response_time_ms - (obj.db_query_time_ms or 0)
            ),
            'database_queries_count': obj.db_query_count,
            'cache_efficiency': obj.cache_hit,
            'response_size_kb': (
                round(obj.response_size_bytes / 1024, 2)
                if obj.response_size_bytes else None
            ),
            'performance_category': self._get_performance_category(obj),
            'optimization_suggestions': self._get_optimization_suggestions(obj)
        }
    
    def get_request_context(self, obj):
        """Return request context information"""
        return {
            'has_user': obj.user is not None,
            'is_authenticated_request': obj.user is not None,
            'is_successful': obj.status_code < 400,
            'is_client_error': 400 <= obj.status_code < 500,
            'is_server_error': obj.status_code >= 500,
            'has_cache_hit': obj.cache_hit is True,
            'timestamp_age_minutes': (
                timezone.now() - obj.timestamp
            ).total_seconds() / 60,
            'server_info': {
                'server_name': obj.server_name,
                'process_id': obj.process_id
            }
        }
    
    def _get_performance_category(self, obj):
        """Categorize performance based on response time"""
        if obj.response_time_ms < 100:
            return 'excellent'
        elif obj.response_time_ms < 300:
            return 'good'
        elif obj.response_time_ms < 1000:
            return 'acceptable'
        elif obj.response_time_ms < 3000:
            return 'slow'
        else:
            return 'very_slow'
    
    def _get_optimization_suggestions(self, obj):
        """Provide optimization suggestions based on metrics"""
        suggestions = []
        
        if obj.response_time_ms > 1000:
            suggestions.append('Consider optimizing slow response time')
        
        if obj.db_query_count > 10:
            suggestions.append('High number of database queries - consider query optimization')
        
        if obj.db_query_time_ms and obj.response_time_ms > 0:
            db_percentage = (obj.db_query_time_ms / obj.response_time_ms) * 100
            if db_percentage > 70:
                suggestions.append('Database queries taking significant time - optimize queries or add indexes')
        
        if obj.cache_hit is False and obj.response_time_ms > 500:
            suggestions.append('Consider implementing caching for this endpoint')
        
        if obj.response_size_bytes and obj.response_size_bytes > 1024 * 1024:  # 1MB
            suggestions.append('Large response size - consider pagination or data optimization')
        
        if not suggestions:
            suggestions.append('Performance looks good!')
        
        return suggestions
    
    def validate_endpoint(self, value):
        """Validate endpoint format"""
        if not value or not value.strip():
            raise serializers.ValidationError("Endpoint cannot be empty.")
        if len(value) > 200:
            raise serializers.ValidationError("Endpoint cannot be longer than 200 characters.")
        return value.strip()
    
    def validate_http_method(self, value):
        """Validate HTTP method"""
        valid_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
        if value.upper() not in valid_methods:
            raise serializers.ValidationError(f"Invalid HTTP method. Must be one of: {', '.join(valid_methods)}")
        return value.upper()
    
    def validate_endpoint_category(self, value):
        """Validate endpoint category"""
        valid_categories = dict(ResponseTime.ENDPOINT_CATEGORIES).keys()
        if value not in valid_categories:
            raise serializers.ValidationError(f"Invalid endpoint category. Must be one of: {', '.join(valid_categories)}")
        return value
    
    def validate_response_time_ms(self, value):
        """Validate response time"""
        if value < 0:
            raise serializers.ValidationError("Response time cannot be negative.")
        if value > 300000:  # 5 minutes
            raise serializers.ValidationError("Response time seems unreasonably high (>5 minutes).")
        return value
    
    def validate_status_code(self, value):
        """Validate HTTP status code"""
        if not (100 <= value <= 599):
            raise serializers.ValidationError("Invalid HTTP status code. Must be between 100 and 599.")
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # Validate database query time doesn't exceed total response time
        db_time = data.get('db_query_time_ms')
        response_time = data.get('response_time_ms')
        
        if db_time and response_time and db_time > response_time:
            raise serializers.ValidationError(
                "Database query time cannot exceed total response time."
            )
        
        # Validate query count is reasonable if query time is provided
        db_count = data.get('db_query_count', 0)
        if db_time and db_count == 0:
            raise serializers.ValidationError(
                "Database query count should be greater than 0 if query time is provided."
            )
        
        return data


class ResponseTimeListSerializer(serializers.ModelSerializer):
    """Simplified serializer for response time lists"""
    performance_grade = serializers.ReadOnlyField()
    is_slow = serializers.ReadOnlyField()
    user_info = serializers.SerializerMethodField()
    
    class Meta:
        model = ResponseTime
        fields = [
            'id', 'endpoint', 'http_method', 'endpoint_category',
            'response_time_ms', 'status_code', 'cache_hit',
            'has_error', 'timestamp', 'performance_grade',
            'is_slow', 'user_info'
        ]
        read_only_fields = ['id', 'timestamp', 'performance_grade', 'is_slow', 'user_info']
    
    def get_user_info(self, obj):
        """Return basic user information"""
        if obj.user:
            return {
                'id': obj.user.id,
                'username': obj.user.username
            }
        return None


class ResponseTimeCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating response time records"""
    
    class Meta:
        model = ResponseTime
        fields = [
            'endpoint', 'http_method', 'endpoint_category',
            'response_time_ms', 'db_query_time_ms', 'db_query_count',
            'cache_hit', 'status_code', 'response_size_bytes',
            'ip_address', 'user_agent', 'server_name', 'process_id',
            'has_error', 'error_type', 'error_message'
        ]
    
    def validate_response_time_ms(self, value):
        """Validate response time"""
        if value < 0:
            raise serializers.ValidationError("Response time cannot be negative.")
        return value
    
    def validate_status_code(self, value):
        """Validate status code"""
        if not (100 <= value <= 599):
            raise serializers.ValidationError("Invalid HTTP status code.")
        return value
    
    def create(self, validated_data):
        """Create response time record with user from request context"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        return super().create(validated_data)


class ResponseTimeStatsSerializer(serializers.Serializer):
    """Serializer for response time statistics"""
    endpoint = serializers.CharField()
    avg_response_time = serializers.FloatField()
    min_response_time = serializers.IntegerField()
    max_response_time = serializers.IntegerField()
    total_requests = serializers.IntegerField()
    error_count = serializers.IntegerField()
    error_rate = serializers.FloatField()
    cache_hit_rate = serializers.FloatField()
    avg_db_queries = serializers.FloatField()
    performance_grade = serializers.CharField()
    
    class Meta:
        # This is a non-model serializer for aggregated statistics
        pass 