from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    # Notifications
    path('notifications/', views.NotificationListCreateView.as_view(), name='notification_list_create'),
    path('notifications/<int:pk>/', views.NotificationDetailView.as_view(), name='notification_detail'),
    path('notifications/mark-read/', views.mark_as_read, name='mark_as_read'),
    path('notifications/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('notifications/dismiss/', views.dismiss_notifications, name='dismiss_notifications'),
    path('notifications/summary/', views.notification_summary, name='notification_summary'),
    path('notifications/stats/', views.notification_stats, name='notification_stats'),
    path('notifications/clear-old/', views.clear_old_notifications, name='clear_old_notifications'),
    
    # Notification preferences
    path('preferences/', views.notification_preferences, name='notification_preferences'),
    path('preferences/update/', views.update_notification_preferences, name='update_notification_preferences'),
] 