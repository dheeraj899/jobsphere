from django.shortcuts import render
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils import timezone
from .models import Notification
from .serializers import (
    NotificationSerializer, NotificationCreateSerializer,
    NotificationUpdateSerializer, NotificationListSerializer
)


class NotificationPagination(PageNumberPagination):
    """Custom pagination for notifications"""
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class NotificationListCreateView(generics.ListCreateAPIView):
    """List and create notifications"""
    pagination_class = NotificationPagination
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['notification_type', 'priority', 'is_read', 'is_dismissed']
    ordering_fields = ['created_at', 'priority', 'read_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Use different serializers for list and create"""
        if self.request.method == 'POST':
            return NotificationCreateSerializer
        return NotificationListSerializer
    
    def get_queryset(self):
        """Get notifications for authenticated user"""
        queryset = Notification.objects.filter(user=self.request.user)
        
        # Filter by read status
        unread_only = self.request.query_params.get('unread_only')
        if unread_only and unread_only.lower() == 'true':
            queryset = queryset.filter(is_read=False)
        
        # Filter by active (not dismissed and not expired)
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
                is_dismissed=False
            )
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Enhanced list with notification statistics"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get notification statistics
        stats = self._get_notification_stats(request.user)
        
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
        """Create notification (typically for admin use)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Set user to current user if not specified
        user = request.data.get('user', request.user.id)
        notification = serializer.save(user_id=user)
        
        return Response({
            'message': 'Notification created successfully',
            'notification': NotificationSerializer(notification).data
        }, status=status.HTTP_201_CREATED)
    
    def _get_notification_stats(self, user):
        """Get notification statistics for user"""
        notifications = Notification.objects.filter(user=user)
        
        stats = notifications.aggregate(
            total=Count('id'),
            unread=Count('id', filter=Q(is_read=False)),
            high_priority=Count('id', filter=Q(priority='high', is_read=False)),
            urgent=Count('id', filter=Q(priority='urgent', is_read=False))
        )
        
        # Add type breakdown
        type_stats = {}
        for notification_type, _ in Notification.NOTIFICATION_TYPES:
            count = notifications.filter(
                notification_type=notification_type,
                is_read=False
            ).count()
            if count > 0:
                type_stats[notification_type] = count
        
        stats['by_type'] = type_stats
        return stats


class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete notification"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get notifications for authenticated user"""
        return Notification.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Use different serializer for updates"""
        if self.request.method in ['PUT', 'PATCH']:
            return NotificationUpdateSerializer
        return NotificationSerializer
    
    def retrieve(self, request, *args, **kwargs):
        """Get notification and optionally mark as read"""
        instance = self.get_object()
        
        # Auto-mark as read if requested
        mark_read = request.query_params.get('mark_read')
        if mark_read and mark_read.lower() == 'true' and not instance.is_read:
            instance.is_read = True
            instance.read_at = timezone.now()
            instance.save(update_fields=['is_read', 'read_at'])
        
        serializer = self.get_serializer(instance)
        return Response({
            'notification': serializer.data,
            'marked_read': mark_read and mark_read.lower() == 'true'
        })
    
    def update(self, request, *args, **kwargs):
        """Update notification status"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        notification = serializer.save()
        
        return Response({
            'message': 'Notification updated successfully',
            'notification': NotificationSerializer(notification).data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete notification"""
        instance = self.get_object()
        instance.delete()
        
        return Response({
            'message': 'Notification deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_as_read(request):
    """Mark one or multiple notifications as read"""
    notification_ids = request.data.get('notification_ids', [])
    
    if not notification_ids:
        return Response({
            'error': 'No notification IDs provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Update notifications
    updated_count = Notification.objects.filter(
        id__in=notification_ids,
        user=request.user,
        is_read=False
    ).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    return Response({
        'message': f'{updated_count} notifications marked as read',
        'updated_count': updated_count
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_all_read(request):
    """Mark all notifications as read for the user"""
    notification_type = request.data.get('notification_type')
    
    queryset = Notification.objects.filter(
        user=request.user,
        is_read=False
    )
    
    # Filter by type if specified
    if notification_type:
        queryset = queryset.filter(notification_type=notification_type)
    
    updated_count = queryset.update(
        is_read=True,
        read_at=timezone.now()
    )
    
    return Response({
        'message': f'All notifications marked as read',
        'updated_count': updated_count
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def dismiss_notifications(request):
    """Dismiss one or multiple notifications"""
    notification_ids = request.data.get('notification_ids', [])
    
    if not notification_ids:
        return Response({
            'error': 'No notification IDs provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    updated_count = Notification.objects.filter(
        id__in=notification_ids,
        user=request.user
    ).update(is_dismissed=True)
    
    return Response({
        'message': f'{updated_count} notifications dismissed',
        'updated_count': updated_count
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_summary(request):
    """Get notification summary for user"""
    user = request.user
    
    # Get counts by status
    notifications = Notification.objects.filter(user=user)
    
    summary = {
        'total_notifications': notifications.count(),
        'unread_count': notifications.filter(is_read=False).count(),
        'urgent_count': notifications.filter(
            priority='urgent',
            is_read=False,
            is_dismissed=False
        ).count(),
        'high_priority_count': notifications.filter(
            priority='high',
            is_read=False,
            is_dismissed=False
        ).count(),
        'active_count': notifications.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
            is_dismissed=False
        ).count()
    }
    
    # Get recent notifications
    recent_notifications = notifications.filter(
        is_dismissed=False
    ).order_by('-created_at')[:5]
    
    recent_serializer = NotificationListSerializer(recent_notifications, many=True)
    
    # Get type breakdown
    type_breakdown = {}
    for notification_type, display_name in Notification.NOTIFICATION_TYPES:
        count = notifications.filter(
            notification_type=notification_type,
            is_read=False,
            is_dismissed=False
        ).count()
        if count > 0:
            type_breakdown[notification_type] = {
                'count': count,
                'display_name': display_name
            }
    
    return Response({
        'summary': summary,
        'recent_notifications': recent_serializer.data,
        'type_breakdown': type_breakdown,
        'generated_at': timezone.now()
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_preferences(request):
    """Get user notification preferences"""
    user = request.user
    
    # Get preferences from user dashboard if available
    try:
        from apps.activity.models import Dashboard
        dashboard = Dashboard.objects.get(user=user)
        preferences = dashboard.notification_preferences
    except Dashboard.DoesNotExist:
        # Default preferences
        preferences = {
            'email_notifications': True,
            'push_notifications': True,
            'sms_notifications': False,
            'job_alerts': True,
            'application_updates': True,
            'message_notifications': True,
            'system_notifications': True,
            'marketing_notifications': False
        }
    
    return Response({
        'preferences': preferences
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_notification_preferences(request):
    """Update user notification preferences"""
    user = request.user
    new_preferences = request.data.get('preferences', {})
    
    try:
        from apps.activity.models import Dashboard
        dashboard, created = Dashboard.objects.get_or_create(user=user)
        
        # Update preferences
        dashboard.notification_preferences.update(new_preferences)
        dashboard.save(update_fields=['notification_preferences', 'last_updated'])
        
        return Response({
            'message': 'Notification preferences updated successfully',
            'preferences': dashboard.notification_preferences
        })
        
    except Exception as e:
        return Response({
            'error': 'Failed to update preferences'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def clear_old_notifications(request):
    """Clear old read notifications (older than 30 days)"""
    days = int(request.query_params.get('days', 30))
    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    
    deleted_count, _ = Notification.objects.filter(
        user=request.user,
        is_read=True,
        read_at__lt=cutoff_date
    ).delete()
    
    return Response({
        'message': f'Cleared {deleted_count} old notifications',
        'deleted_count': deleted_count,
        'cutoff_days': days
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_stats(request):
    """Get detailed notification statistics"""
    user = request.user
    days = int(request.query_params.get('days', 30))
    start_date = timezone.now() - timezone.timedelta(days=days)
    
    notifications = Notification.objects.filter(
        user=user,
        created_at__gte=start_date
    )
    
    # Daily notification counts
    daily_stats = notifications.extra(
        select={'day': 'date(created_at)'}
    ).values('day').annotate(
        count=Count('id'),
        unread_count=Count('id', filter=Q(is_read=False))
    ).order_by('day')
    
    # Type statistics
    type_stats = {}
    for notification_type, display_name in Notification.NOTIFICATION_TYPES:
        count = notifications.filter(notification_type=notification_type).count()
        if count > 0:
            type_stats[notification_type] = {
                'count': count,
                'display_name': display_name,
                'unread': notifications.filter(
                    notification_type=notification_type,
                    is_read=False
                ).count()
            }
    
    # Priority statistics
    priority_stats = {}
    for priority, display_name in Notification.PRIORITY_LEVELS:
        count = notifications.filter(priority=priority).count()
        if count > 0:
            priority_stats[priority] = {
                'count': count,
                'display_name': display_name,
                'unread': notifications.filter(
                    priority=priority,
                    is_read=False
                ).count()
            }
    
    return Response({
        'period_days': days,
        'total_notifications': notifications.count(),
        'daily_stats': list(daily_stats),
        'type_stats': type_stats,
        'priority_stats': priority_stats,
        'generated_at': timezone.now()
    })
