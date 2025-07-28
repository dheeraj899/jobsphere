from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Region, Location, LocationHistory


class RegionSerializer(serializers.ModelSerializer):
    """Region serializer with validation"""
    location_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Region
        fields = [
            'id', 'name', 'code', 'country', 'state_province',
            'latitude_min', 'latitude_max', 'longitude_min', 'longitude_max',
            'timezone', 'is_active', 'created_at', 'updated_at', 'location_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'location_count']
    
    def get_location_count(self, obj):
        """Return count of locations in this region"""
        return obj.locations.filter(is_verified=True).count()
    
    def validate_code(self, value):
        """Validate region code format"""
        if not value.isupper():
            raise serializers.ValidationError("Region code should be uppercase.")
        if len(value) < 2 or len(value) > 10:
            raise serializers.ValidationError("Region code should be between 2 and 10 characters.")
        return value
    
    def validate(self, data):
        """Validate geographical boundaries"""
        lat_min = data.get('latitude_min')
        lat_max = data.get('latitude_max')
        lon_min = data.get('longitude_min')
        lon_max = data.get('longitude_max')
        
        if lat_min is not None and lat_max is not None:
            if lat_min >= lat_max:
                raise serializers.ValidationError("Minimum latitude must be less than maximum latitude.")
            if lat_min < -90 or lat_min > 90:
                raise serializers.ValidationError("Latitude must be between -90 and 90.")
            if lat_max < -90 or lat_max > 90:
                raise serializers.ValidationError("Latitude must be between -90 and 90.")
        
        if lon_min is not None and lon_max is not None:
            if lon_min >= lon_max:
                raise serializers.ValidationError("Minimum longitude must be less than maximum longitude.")
            if lon_min < -180 or lon_min > 180:
                raise serializers.ValidationError("Longitude must be between -180 and 180.")
            if lon_max < -180 or lon_max > 180:
                raise serializers.ValidationError("Longitude must be between -180 and 180.")
        
        return data


class LocationSerializer(serializers.ModelSerializer):
    """Basic location serializer for nested relationships"""
    full_address = serializers.ReadOnlyField()
    
    class Meta:
        ref_name = 'MapLocationSerializer'
        model = Location
        fields = ['id', 'name', 'city', 'state_province', 'country', 'latitude', 'longitude', 'full_address']
        read_only_fields = ['id', 'full_address']
    
    def get_job_count(self, obj):
        """Return count of active jobs at this location"""
        return obj.jobs.filter(status='active').count()
    
    def validate_name(self, value):
        """Validate location name"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Location name must be at least 2 characters long.")
        return value.strip()
    
    def validate_city(self, value):
        """Validate city name"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("City name must be at least 2 characters long.")
        return value.strip()
    
    def validate_country(self, value):
        """Validate country name"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Country name must be at least 2 characters long.")
        return value.strip()
    
    def validate_latitude(self, value):
        """Validate latitude range"""
        if value is not None and (value < -90 or value > 90):
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value
    
    def validate_longitude(self, value):
        """Validate longitude range"""
        if value is not None and (value < -180 or value > 180):
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value
    
    def validate_region_id(self, value):
        """Validate region exists if provided"""
        if value is not None:
            try:
                Region.objects.get(id=value, is_active=True)
            except Region.DoesNotExist:
                raise serializers.ValidationError("Invalid region or region is not active.")
        return value
    
    def create(self, validated_data):
        """Create location with user from request"""
        if 'created_by' not in validated_data and self.context.get('request'):
            validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class LocationListSerializer(serializers.ModelSerializer):
    """Simplified location serializer for list views"""
    region_name = serializers.CharField(source='region.name', read_only=True)
    job_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Location
        fields = [
            'id', 'name', 'city', 'state_province', 'country',
            'latitude', 'longitude', 'location_type', 'region_name',
            'is_verified', 'is_remote_friendly', 'job_count'
        ]
    
    def get_job_count(self, obj):
        """Return count of active jobs at this location"""
        return obj.jobs.filter(status='active').count()


class LocationHistorySerializer(serializers.ModelSerializer):
    """Location history serializer for tracking searches"""
    user = serializers.StringRelatedField(read_only=True)
    location = LocationListSerializer(read_only=True)
    location_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = LocationHistory
        fields = [
            'id', 'user', 'location', 'location_id', 'search_query',
            'search_context', 'searched_at'
        ]
        read_only_fields = ['id', 'user', 'searched_at']
    
    def validate_location_id(self, value):
        """Validate location exists"""
        try:
            Location.objects.get(id=value)
        except Location.DoesNotExist:
            raise serializers.ValidationError("Location does not exist.")
        return value
    
    def create(self, validated_data):
        """Create location history with user from request"""
        if self.context.get('request'):
            validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class LocationNearbySerializer(serializers.Serializer):
    """Serializer for nearby location search"""
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    radius_km = serializers.IntegerField(min_value=1, max_value=100, default=10)
    location_type = serializers.CharField(required=False)
    
    def validate_latitude(self, value):
        """Validate latitude range"""
        if value < -90 or value > 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90.")
        return value
    
    def validate_longitude(self, value):
        """Validate longitude range"""
        if value < -180 or value > 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180.")
        return value 