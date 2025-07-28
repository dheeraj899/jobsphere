from rest_framework import serializers
from django.contrib.auth.models import User

# Note: No models are currently defined in the navigation app
# This file provides a basic structure for when navigation models are added

class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested relationships"""
    class Meta:
        ref_name = 'NavigationUserBasic'
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']
        read_only_fields = ['id', 'username']


# Example serializers that could be implemented when navigation models are added:

# class MenuItemSerializer(serializers.ModelSerializer):
#     """Menu item serializer"""
#     pass

# class NavigationBreadcrumbSerializer(serializers.ModelSerializer):
#     """Navigation breadcrumb serializer"""
#     pass

# class UserNavigationPreferencesSerializer(serializers.ModelSerializer):
#     """User navigation preferences serializer"""
#     pass

# Placeholder comment - implement serializers here when navigation models are defined 