from django.shortcuts import render
from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from .models import Region, Location, LocationHistory
from .serializers import (
    RegionSerializer, LocationSerializer, LocationListSerializer,
    LocationHistorySerializer, LocationNearbySerializer
)
from django.utils import timezone
from datetime import timedelta
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class MapPagination(PageNumberPagination):
    """Custom pagination for map-related views"""
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class RegionListView(generics.ListAPIView):
    """List all active regions"""
    serializer_class = RegionSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = MapPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['country', 'state_province', 'is_active']
    search_fields = ['name', 'code', 'country', 'state_province']
    ordering_fields = ['name', 'country', 'created_at']
    ordering = ['country', 'state_province', 'name']
    
    def get_queryset(self):
        """Get active regions with location counts"""
        return Region.objects.filter(is_active=True).annotate(
            location_count=Count('locations', filter=Q(locations__is_verified=True))
        )


class RegionDetailView(generics.RetrieveAPIView):
    """Get region details with locations"""
    serializer_class = RegionSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """Get regions with location data"""
        return Region.objects.filter(is_active=True).annotate(
            location_count=Count('locations', filter=Q(locations__is_verified=True))
        )
    
    def retrieve(self, request, *args, **kwargs):
        """Get region with its locations"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Get locations in this region
        locations = Location.objects.filter(
            region=instance,
            is_verified=True
        ).order_by('name')[:20]  # Limit to first 20
        
        location_serializer = LocationListSerializer(locations, many=True)
        
        return Response({
            'region': serializer.data,
            'locations': location_serializer.data,
            'total_locations': instance.location_count
        })


class LocationListCreateView(generics.ListCreateAPIView):
    """List and create locations"""
    pagination_class = MapPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['region', 'country', 'location_type', 'is_verified']
    search_fields = ['name', 'city', 'state_province', 'country', 'address']
    ordering_fields = ['name', 'city', 'created_at']
    ordering = ['country', 'city', 'name']
    
    def get_serializer_class(self):
        """Use different serializers for list and create"""
        if self.request.method == 'POST':
            return LocationSerializer
        return LocationListSerializer
    
    def get_permissions(self):
        """Different permissions for list vs create"""
        if self.request.method == 'POST':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Get verified locations with job counts"""
        return Location.objects.filter(is_verified=True).select_related('region')
    
    def list(self, request, *args, **kwargs):
        """Enhanced list with metadata"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get location statistics
        stats = {
            'total_locations': queryset.count(),
            'countries': queryset.values_list('country', flat=True).distinct().count(),
        }
        
        # Add distance info if coordinates provided
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        if lat and lng:
            stats['search_center'] = {'lat': float(lat), 'lng': float(lng)}
            stats['radius_km'] = float(request.query_params.get('radius', '50'))
        
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
    
    def perform_create(self, serializer):
        """Create location with created_by set to current user"""
        serializer.save(created_by=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Create location with validation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        location = serializer.save(created_by=request.user, is_verified=False)
        
        return Response({
            'message': 'Location created successfully. It will be verified by administrators.',
            'location': LocationSerializer(location).data
        }, status=status.HTTP_201_CREATED)


class LocationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete location"""
    serializer_class = LocationSerializer
    
    def get_permissions(self):
        """Different permissions based on method"""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Get locations based on user permissions"""
        if self.request.user.is_authenticated:
            # Authenticated users can see their own unverified locations
            return Location.objects.filter(
                Q(is_verified=True) | Q(created_by=self.request.user)
            ).select_related('region', 'created_by')
        else:
            # Anonymous users only see verified locations
            return Location.objects.filter(is_verified=True).select_related('region')
    
    def retrieve(self, request, *args, **kwargs):
        """Get location with additional context"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response({
            'location': serializer.data,
            'can_edit': (
                request.user.is_authenticated and 
                (instance.created_by == request.user or request.user.is_staff)
            )
        })
    
    def update(self, request, *args, **kwargs):
        """Update location (only by creator or staff)"""
        instance = self.get_object()
        
        if not (instance.created_by == request.user or request.user.is_staff):
            return Response({
                'error': 'You can only edit locations you created'
            }, status=status.HTTP_403_FORBIDDEN)
        
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # If user is not staff, mark as unverified for re-review
        if not request.user.is_staff:
            serializer.save(is_verified=False)
        else:
            serializer.save()
        
        return Response({
            'message': 'Location updated successfully',
            'location': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete location (only by creator or staff)"""
        instance = self.get_object()
        
        if not (instance.created_by == request.user or request.user.is_staff):
            return Response({
                'error': 'You can only delete locations you created'
            }, status=status.HTTP_403_FORBIDDEN)
        
        instance.delete()
        return Response({
            'message': 'Location deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


class LocationHistoryView(generics.ListCreateAPIView):
    """List and create location search history"""
    serializer_class = LocationHistorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MapPagination
    ordering = ['-searched_at']
    
    def get_queryset(self):
        """Get location history for authenticated user"""
        return LocationHistory.objects.filter(
            user=self.request.user
        ).select_related('location')
    
    def perform_create(self, serializer):
        """Create location history entry"""
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Create location history entry with duplicate handling"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check for recent duplicate
        location_id = request.data.get('location')
        query = request.data.get('query', '')
        
        recent_history = LocationHistory.objects.filter(
            user=request.user,
            location_id=location_id,
            query=query,
            searched_at__gte=timezone.now() - timedelta(minutes=5)
        ).first()
        
        if recent_history:
            return Response({
                'message': 'Recent search found',
                'history': LocationHistorySerializer(recent_history).data
            }, status=status.HTTP_200_OK)
        
        history = serializer.save(user=request.user)
        
        return Response({
            'message': 'Location search recorded',
            'history': LocationHistorySerializer(history).data
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def search_nearby(request):
    """Nearby search disabled (GDAL removed)"""
    return Response({'locations': []})


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def popular_locations(request):
    """Get popular locations based on job postings and searches"""
    # Get locations with most jobs
    from apps.jobs.models import Job
    
    popular_locations = Location.objects.filter(
        is_verified=True
    ).annotate(
        job_count=Count('job_set', filter=Q(job_set__status='published'))
    ).filter(job_count__gt=0).order_by('-job_count')[:20]
    
    serializer = LocationListSerializer(popular_locations, many=True)
    
    return Response({
        'popular_locations': serializer.data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def location_suggestions(request):
    """Get location suggestions based on query"""
    query = request.query_params.get('q', '').strip()
    if not query or len(query) < 2:
        return Response({
            'suggestions': []
        })
    
    # Search in multiple fields
    locations = Location.objects.filter(
        Q(name__icontains=query) |
        Q(city__icontains=query) |
        Q(state_province__icontains=query) |
        Q(country__icontains=query),
        is_verified=True
    ).distinct()[:10]
    
    suggestions = []
    for location in locations:
        suggestions.append({
            'id': location.id,
            'name': location.name,
            'full_name': location.full_address,
            'type': location.location_type,
            'coordinates': [location.latitude, location.longitude] if location.coordinates else None
        })
    
    return Response({
        'suggestions': suggestions,
        'query': query
    })
