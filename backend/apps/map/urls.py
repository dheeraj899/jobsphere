from django.urls import path
from . import views
from django.views.decorators.cache import cache_page

app_name = 'map'

urlpatterns = [
    # Regions
    path('regions/', cache_page(300)(views.RegionListView.as_view()), name='region_list'),
    path('regions/<int:pk>/', cache_page(300)(views.RegionDetailView.as_view()), name='region_detail'),
    
    # Locations
    path('locations/', views.LocationListCreateView.as_view(), name='location_list_create'),
    path('locations/<int:pk>/', views.LocationDetailView.as_view(), name='location_detail'),
    path('locations/search/nearby/', views.search_nearby, name='search_nearby'),
    path('locations/popular/', views.popular_locations, name='popular_locations'),
    path('locations/suggestions/', views.location_suggestions, name='location_suggestions'),
    
    # Location history
    path('history/', views.LocationHistoryView.as_view(), name='location_history'),
] 