from django.contrib import admin
from .models import Region, Location, LocationHistory

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'state_province', 'is_active')
    list_filter = ('country', 'state_province', 'is_active')
    search_fields = ('name', 'code')

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'country', 'location_type', 'is_verified', 'created_by')
    list_filter = ('location_type', 'is_verified', 'country')
    search_fields = ('name', 'city', 'address')
    raw_id_fields = ('created_by',)

@admin.register(LocationHistory)
class LocationHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'searched_at')
    list_filter = ('searched_at',)
    search_fields = ('user__username', 'location__name')
