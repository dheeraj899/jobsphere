from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Notification


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested relationships"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        ref_name = 'MessagingUserBasic'
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name']
        read_only_fields = ['id', 'username']
    
    def get_full_name(self, obj):
        """Return user's full name"""
        return f"{obj.first_name} {obj.last_name}".strip()


class NotificationSerializer(serializers.ModelSerializer):
    """Notification serializer with validation and computed fields"""
    user = UserBasicSerializer(read_only=True)
    time_since_created = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    delivery_status = serializers.SerializerMethodField()
    action_available = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'notification_type', 'title', 'message',
            'priority', 'action_url', 'action_text', 'related_object_type',
            'related_object_id', 'is_read', 'is_dismissed',
            'email_sent', 'push_sent', 'sms_sent', 'metadata',
            'created_at', 'read_at', 'expires_at', 'time_since_created',
            'is_expired', 'delivery_status', 'action_available'
        ]
        read_only_fields = [
            'id', 'user', 'email_sent', 'push_sent', 'sms_sent',
            'created_at', 'read_at', 'time_since_created',
            'is_expired', 'delivery_status', 'action_available'
        ]
    
    def get_time_since_created(self, obj):
        """Return human-readable time since notification was created"""
        time_diff = timezone.now() - obj.created_at
        
        if time_diff.days > 0:
            return f"{time_diff.days} days ago"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            return f"{hours} hours ago"
        elif time_diff.seconds > 60:
            minutes = time_diff.seconds // 60
            return f"{minutes} minutes ago"
        else:
            return "Just now"
    
    def get_is_expired(self, obj):
        """Check if notification has expired"""
        if obj.expires_at:
            return timezone.now() > obj.expires_at
        return False
    
    def get_delivery_status(self, obj):
        """Return delivery status summary"""
        channels_sent = []
        if obj.email_sent:
            channels_sent.append('email')
        if obj.push_sent:
            channels_sent.append('push')
        if obj.sms_sent:
            channels_sent.append('sms')
        
        return {
            'channels_sent': channels_sent,
            'total_channels': len(channels_sent),
            'all_channels_sent': len(channels_sent) == 3
        }
    
    def get_action_available(self, obj):
        """Check if notification has an available action"""
        return bool(obj.action_url and obj.action_text)
    
    def validate_notification_type(self, value):
        """Validate notification type"""
        valid_types = dict(Notification.NOTIFICATION_TYPES).keys()
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid notification type. Must be one of: {', '.join(valid_types)}")
        return value
    
    def validate_priority(self, value):
        """Validate priority level"""
        valid_priorities = dict(Notification.PRIORITY_LEVELS).keys()
        if value not in valid_priorities:
            raise serializers.ValidationError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")
        return value
    
    def validate_title(self, value):
        """Validate notification title"""
        if not value or not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        if len(value) > 200:
            raise serializers.ValidationError("Title cannot be longer than 200 characters.")
        return value.strip()
    
    def validate_message(self, value):
        """Validate notification message"""
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty.")
        if len(value) > 5000:
            raise serializers.ValidationError("Message cannot be longer than 5000 characters.")
        return value.strip()
    
    def validate_action_text(self, value):
        """Validate action text"""
        if value and len(value) > 100:
            raise serializers.ValidationError("Action text cannot be longer than 100 characters.")
        return value
    
    def validate_expires_at(self, value):
        """Validate expiration date"""
        if value and value <= timezone.now():
            raise serializers.ValidationError("Expiration date must be in the future.")
        return value
    
    def validate_metadata(self, value):
        """Validate metadata JSON structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a valid JSON object.")
        
        # Check metadata size (prevent extremely large payloads)
        import json
        metadata_size = len(json.dumps(value))
        if metadata_size > 10240:  # 10KB limit
            raise serializers.ValidationError("Metadata is too large. Maximum size is 10KB.")
        
        return value
    
    def validate(self, data):
        """Cross-field validation"""
        # If action_url is provided, action_text should also be provided
        action_url = data.get('action_url')
        action_text = data.get('action_text')
        
        if action_url and not action_text:
            raise serializers.ValidationError("Action text is required when action URL is provided.")
        
        if action_text and not action_url:
            raise serializers.ValidationError("Action URL is required when action text is provided.")
        
        return data


class NotificationCreateSerializer(serializers.ModelSerializer):
    """Simplified serializer for creating notifications"""
    
    class Meta:
        model = Notification
        fields = [
            'notification_type', 'title', 'message', 'priority',
            'action_url', 'action_text', 'related_object_type',
            'related_object_id', 'metadata', 'expires_at'
        ]
    
    def validate_notification_type(self, value):
        """Validate notification type"""
        valid_types = dict(Notification.NOTIFICATION_TYPES).keys()
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid notification type. Must be one of: {', '.join(valid_types)}")
        return value
    
    def validate_priority(self, value):
        """Validate priority level"""
        valid_priorities = dict(Notification.PRIORITY_LEVELS).keys()
        if value not in valid_priorities:
            raise serializers.ValidationError(f"Invalid priority. Must be one of: {', '.join(valid_priorities)}")
        return value


class NotificationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating notification status"""
    
    class Meta:
        model = Notification
        fields = ['is_read', 'is_dismissed']
    
    def update(self, instance, validated_data):
        """Update notification and set read_at timestamp if marked as read"""
        if validated_data.get('is_read') and not instance.is_read:
            instance.read_at = timezone.now()
        
        return super().update(instance, validated_data)


class NotificationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for notification lists"""
    time_since_created = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'priority',
            'action_url', 'action_text', 'is_read', 'is_dismissed',
            'created_at', 'expires_at', 'time_since_created', 'is_expired'
        ]
        read_only_fields = ['id', 'created_at', 'time_since_created', 'is_expired']
    
    def get_time_since_created(self, obj):
        """Return human-readable time since notification was created"""
        time_diff = timezone.now() - obj.created_at
        
        if time_diff.days > 0:
            return f"{time_diff.days}d"
        elif time_diff.seconds > 3600:
            hours = time_diff.seconds // 3600
            return f"{hours}h"
        elif time_diff.seconds > 60:
            minutes = time_diff.seconds // 60
            return f"{minutes}m"
        else:
            return "now"
    
    def get_is_expired(self, obj):
        """Check if notification has expired"""
        if obj.expires_at:
            return timezone.now() > obj.expires_at
        return False 