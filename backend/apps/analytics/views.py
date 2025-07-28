from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Avg, Max, Min, Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import ResponseTime
from .serializers import (
    ResponseTimeSerializer, ResponseTimeListSerializer,
    ResponseTimeCreateSerializer, ResponseTimeStatsSerializer
)
from apps.analytics.tasks import aggregate_analytics


class AnalyticsPagination(PageNumberPagination):
    """Custom pagination for analytics views"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class ResponseTimeListCreateView(generics.ListCreateAPIView):
    """List and create response time records"""
    pagination_class = AnalyticsPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = [
        'endpoint_category', 'http_method', 'status_code',
        'has_error', 'cache_hit', 'server_name'
    ]
    ordering_fields = ['response_time_ms', 'timestamp', 'status_code']
    ordering = ['-timestamp']
    
    def get_serializer_class(self):
        """Use different serializers for list and create"""
        if self.request.method == 'POST':
            return ResponseTimeCreateSerializer
        return ResponseTimeListSerializer
    
    def get_permissions(self):
        """Different permissions for list vs create"""
        if self.request.method == 'POST':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAdminUser]  # Only admins can view analytics
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Get response times with filtering"""
        queryset = ResponseTime.objects.select_related('user')
        
        # Filter by time range
        hours = self.request.query_params.get('hours')
        if hours:
            try:
                hours = int(hours)
                start_time = timezone.now() - timedelta(hours=hours)
                queryset = queryset.filter(timestamp__gte=start_time)
            except ValueError:
                pass
        
        # Filter by slow responses
        slow_only = self.request.query_params.get('slow_only')
        if slow_only and slow_only.lower() == 'true':
            queryset = queryset.filter(response_time_ms__gt=2000)
        
        # Filter by errors
        errors_only = self.request.query_params.get('errors_only')
        if errors_only and errors_only.lower() == 'true':
            queryset = queryset.filter(has_error=True)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Enhanced list with performance statistics"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get performance statistics
        stats = queryset.aggregate(
            total_requests=Count('id'),
            avg_response_time=Avg('response_time_ms'),
            min_response_time=Min('response_time_ms'),
            max_response_time=Max('response_time_ms'),
            error_count=Count('id', filter=Q(has_error=True)),
            slow_requests=Count('id', filter=Q(response_time_ms__gt=2000)),
            cache_hits=Count('id', filter=Q(cache_hit=True)),
            cache_total=Count('id', filter=Q(cache_hit__isnull=False))
        )
        
        # Calculate derived metrics
        if stats['total_requests'] > 0:
            stats['error_rate'] = (stats['error_count'] / stats['total_requests']) * 100
            stats['slow_request_rate'] = (stats['slow_requests'] / stats['total_requests']) * 100
        else:
            stats['error_rate'] = 0
            stats['slow_request_rate'] = 0
        
        if stats['cache_total'] > 0:
            stats['cache_hit_rate'] = (stats['cache_hits'] / stats['cache_total']) * 100
        else:
            stats['cache_hit_rate'] = 0
        
        # Round floating point numbers
        for key, value in stats.items():
            if isinstance(value, float):
                stats[key] = round(value, 2)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data['stats'] = stats
            return response
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'stats': stats
        })
    
    def create(self, request, *args, **kwargs):
        """Create response time record"""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        response_time = serializer.save()
        
        return Response({
            'message': 'Response time recorded successfully',
            'id': response_time.id
        }, status=status.HTTP_201_CREATED)


class ResponseTimeDetailView(generics.RetrieveAPIView):
    """Get detailed response time record"""
    serializer_class = ResponseTimeSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        """Get response time records"""
        return ResponseTime.objects.select_related('user')


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def endpoint_performance(request):
    """Get performance statistics by endpoint"""
    hours = int(request.query_params.get('hours', 24))
    start_time = timezone.now() - timedelta(hours=hours)
    
    # Group by endpoint and calculate stats
    endpoint_stats = ResponseTime.objects.filter(
        timestamp__gte=start_time
    ).values('endpoint', 'http_method').annotate(
        total_requests=Count('id'),
        avg_response_time=Avg('response_time_ms'),
        min_response_time=Min('response_time_ms'),
        max_response_time=Max('response_time_ms'),
        error_count=Count('id', filter=Q(has_error=True)),
        slow_requests=Count('id', filter=Q(response_time_ms__gt=2000)),
        cache_hits=Count('id', filter=Q(cache_hit=True)),
        cache_total=Count('id', filter=Q(cache_hit__isnull=False))
    ).order_by('-total_requests')
    
    # Calculate derived metrics
    for stat in endpoint_stats:
        stat['error_rate'] = (stat['error_count'] / stat['total_requests']) * 100 if stat['total_requests'] > 0 else 0
        stat['slow_request_rate'] = (stat['slow_requests'] / stat['total_requests']) * 100 if stat['total_requests'] > 0 else 0
        stat['cache_hit_rate'] = (stat['cache_hits'] / stat['cache_total']) * 100 if stat['cache_total'] > 0 else 0
        
        # Round floating point numbers
        for key, value in stat.items():
            if isinstance(value, float):
                stat[key] = round(value, 2)
    
    return Response({
        'endpoint_stats': list(endpoint_stats[:50]),  # Limit to top 50 endpoints
        'period_hours': hours,
        'generated_at': timezone.now()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def performance_trends(request):
    """Get performance trends over time"""
    hours = int(request.query_params.get('hours', 24))
    interval = request.query_params.get('interval', 'hour')  # hour, day
    
    start_time = timezone.now() - timedelta(hours=hours)
    
    # Build time-based aggregation
    if interval == 'hour':
        time_format = '%Y-%m-%d %H:00:00'
        time_truncate = 'hour'
    else:
        time_format = '%Y-%m-%d'
        time_truncate = 'day'
    
    # Get time-series data
    trends = ResponseTime.objects.filter(
        timestamp__gte=start_time
    ).extra(
        select={'time_bucket': f"date_trunc('{time_truncate}', timestamp)"}
    ).values('time_bucket').annotate(
        total_requests=Count('id'),
        avg_response_time=Avg('response_time_ms'),
        error_count=Count('id', filter=Q(has_error=True)),
        slow_requests=Count('id', filter=Q(response_time_ms__gt=2000))
    ).order_by('time_bucket')
    
    # Calculate rates
    for trend in trends:
        trend['error_rate'] = (trend['error_count'] / trend['total_requests']) * 100 if trend['total_requests'] > 0 else 0
        trend['slow_request_rate'] = (trend['slow_requests'] / trend['total_requests']) * 100 if trend['total_requests'] > 0 else 0
        
        # Round values
        for key, value in trend.items():
            if isinstance(value, float):
                trend[key] = round(value, 2)
    
    return Response({
        'trends': list(trends),
        'period_hours': hours,
        'interval': interval,
        'generated_at': timezone.now()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def error_analysis(request):
    """Analyze errors and their patterns"""
    hours = int(request.query_params.get('hours', 24))
    start_time = timezone.now() - timedelta(hours=hours)
    
    errors = ResponseTime.objects.filter(
        timestamp__gte=start_time,
        has_error=True
    )
    
    # Error type analysis
    error_types = errors.values('error_type').annotate(
        count=Count('id'),
        avg_response_time=Avg('response_time_ms')
    ).order_by('-count')
    
    # Status code analysis
    status_codes = errors.values('status_code').annotate(
        count=Count('id'),
        avg_response_time=Avg('response_time_ms')
    ).order_by('-count')
    
    # Endpoint error analysis
    endpoint_errors = errors.values('endpoint', 'http_method').annotate(
        error_count=Count('id'),
        unique_error_types=Count('error_type', distinct=True)
    ).order_by('-error_count')[:20]
    
    return Response({
        'error_summary': {
            'total_errors': errors.count(),
            'unique_error_types': errors.values('error_type').distinct().count(),
            'affected_endpoints': errors.values('endpoint').distinct().count()
        },
        'error_types': list(error_types),
        'status_codes': list(status_codes),
        'endpoint_errors': list(endpoint_errors),
        'period_hours': hours,
        'generated_at': timezone.now()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def cache_performance(request):
    """Analyze cache performance"""
    hours = int(request.query_params.get('hours', 24))
    start_time = timezone.now() - timedelta(hours=hours)
    
    records = ResponseTime.objects.filter(
        timestamp__gte=start_time,
        cache_hit__isnull=False
    )
    
    # Overall cache stats
    cache_stats = records.aggregate(
        total_requests=Count('id'),
        cache_hits=Count('id', filter=Q(cache_hit=True)),
        cache_misses=Count('id', filter=Q(cache_hit=False)),
        avg_hit_time=Avg('response_time_ms', filter=Q(cache_hit=True)),
        avg_miss_time=Avg('response_time_ms', filter=Q(cache_hit=False))
    )
    
    cache_hit_rate = (cache_stats['cache_hits'] / cache_stats['total_requests']) * 100 if cache_stats['total_requests'] > 0 else 0
    time_saved = (cache_stats['avg_miss_time'] - cache_stats['avg_hit_time']) if cache_stats['avg_hit_time'] and cache_stats['avg_miss_time'] else 0
    
    # Cache performance by endpoint
    endpoint_cache = records.values('endpoint', 'http_method').annotate(
        total_requests=Count('id'),
        cache_hits=Count('id', filter=Q(cache_hit=True)),
        avg_hit_time=Avg('response_time_ms', filter=Q(cache_hit=True)),
        avg_miss_time=Avg('response_time_ms', filter=Q(cache_hit=False))
    ).order_by('-total_requests')[:20]
    
    # Calculate hit rates
    for endpoint in endpoint_cache:
        endpoint['hit_rate'] = (endpoint['cache_hits'] / endpoint['total_requests']) * 100 if endpoint['total_requests'] > 0 else 0
        endpoint['time_saved'] = (endpoint['avg_miss_time'] - endpoint['avg_hit_time']) if endpoint['avg_hit_time'] and endpoint['avg_miss_time'] else 0
    
    return Response({
        'cache_summary': {
            'total_requests': cache_stats['total_requests'],
            'cache_hit_rate': round(cache_hit_rate, 2),
            'avg_hit_time': round(cache_stats['avg_hit_time'], 2) if cache_stats['avg_hit_time'] else 0,
            'avg_miss_time': round(cache_stats['avg_miss_time'], 2) if cache_stats['avg_miss_time'] else 0,
            'time_saved_per_hit': round(time_saved, 2) if time_saved else 0
        },
        'endpoint_cache_performance': list(endpoint_cache),
        'period_hours': hours,
        'generated_at': timezone.now()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def database_performance(request):
    """Analyze database query performance"""
    hours = int(request.query_params.get('hours', 24))
    start_time = timezone.now() - timedelta(hours=hours)
    
    records = ResponseTime.objects.filter(
        timestamp__gte=start_time,
        db_query_time_ms__isnull=False
    )
    
    # Database performance stats
    db_stats = records.aggregate(
        total_requests=Count('id'),
        avg_db_time=Avg('db_query_time_ms'),
        max_db_time=Max('db_query_time_ms'),
        avg_query_count=Avg('db_query_count'),
        max_query_count=Max('db_query_count')
    )
    
    # Slow database queries
    slow_db_queries = records.filter(
        db_query_time_ms__gt=1000  # Queries taking more than 1 second
    ).values('endpoint', 'http_method').annotate(
        slow_query_count=Count('id'),
        avg_db_time=Avg('db_query_time_ms'),
        max_db_time=Max('db_query_time_ms')
    ).order_by('-avg_db_time')[:20]
    
    # High query count endpoints
    high_query_endpoints = records.filter(
        db_query_count__gt=10  # More than 10 queries
    ).values('endpoint', 'http_method').annotate(
        avg_query_count=Avg('db_query_count'),
        max_query_count=Max('db_query_count'),
        request_count=Count('id')
    ).order_by('-avg_query_count')[:20]
    
    return Response({
        'database_summary': {
            'total_requests_with_db': db_stats['total_requests'],
            'avg_db_time': round(db_stats['avg_db_time'], 2) if db_stats['avg_db_time'] else 0,
            'max_db_time': db_stats['max_db_time'] or 0,
            'avg_query_count': round(db_stats['avg_query_count'], 2) if db_stats['avg_query_count'] else 0,
            'max_query_count': db_stats['max_query_count'] or 0
        },
        'slow_db_queries': list(slow_db_queries),
        'high_query_endpoints': list(high_query_endpoints),
        'period_hours': hours,
        'generated_at': timezone.now()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def system_health(request):
    """Get overall system health metrics"""
    hours = int(request.query_params.get('hours', 1))  # Default to last hour
    start_time = timezone.now() - timedelta(hours=hours)
    
    records = ResponseTime.objects.filter(timestamp__gte=start_time)
    
    # Overall health metrics
    health_stats = records.aggregate(
        total_requests=Count('id'),
        avg_response_time=Avg('response_time_ms'),
        error_count=Count('id', filter=Q(has_error=True)),
        slow_requests=Count('id', filter=Q(response_time_ms__gt=2000)),
        very_slow_requests=Count('id', filter=Q(response_time_ms__gt=5000))
    )
    
    # Calculate health score (0-100)
    health_score = 100
    if health_stats['total_requests'] > 0:
        error_rate = (health_stats['error_count'] / health_stats['total_requests']) * 100
        slow_rate = (health_stats['slow_requests'] / health_stats['total_requests']) * 100
        very_slow_rate = (health_stats['very_slow_requests'] / health_stats['total_requests']) * 100
        
        # Deduct points for issues
        health_score -= min(error_rate * 2, 40)  # Max 40 points for errors
        health_score -= min(slow_rate, 30)       # Max 30 points for slow requests
        health_score -= min(very_slow_rate * 2, 30)  # Max 30 points for very slow requests
        
        health_score = max(0, health_score)
    
    # Determine health status
    if health_score >= 90:
        health_status = 'excellent'
    elif health_score >= 75:
        health_status = 'good'
    elif health_score >= 60:
        health_status = 'fair'
    elif health_score >= 40:
        health_status = 'poor'
    else:
        health_status = 'critical'
    
    return Response({
        'health_score': round(health_score, 1),
        'health_status': health_status,
        'metrics': {
            'total_requests': health_stats['total_requests'],
            'avg_response_time': round(health_stats['avg_response_time'], 2) if health_stats['avg_response_time'] else 0,
            'error_rate': round((health_stats['error_count'] / health_stats['total_requests']) * 100, 2) if health_stats['total_requests'] > 0 else 0,
            'slow_request_rate': round((health_stats['slow_requests'] / health_stats['total_requests']) * 100, 2) if health_stats['total_requests'] > 0 else 0,
            'very_slow_request_rate': round((health_stats['very_slow_requests'] / health_stats['total_requests']) * 100, 2) if health_stats['total_requests'] > 0 else 0
        },
        'period_hours': hours,
        'generated_at': timezone.now()
    })
