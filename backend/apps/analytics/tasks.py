from celery import shared_task
from django.db.models import Count, Avg, Q
from .models import ResponseTime

@shared_task
def aggregate_analytics():
    """Aggregate analytics data periodically"""
    stats = ResponseTime.objects.aggregate(
        total_requests=Count('id'),
        avg_response_time=Avg('response_time_ms'),
        error_count=Count('id', filter=Q(has_error=True))
    )
    # Optionally, store stats or log them
    return stats 