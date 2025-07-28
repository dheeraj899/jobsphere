from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, F
from django.utils import timezone
from .models import Category, SearchQuery, PopularSearch, SearchSuggestion, SavedSearch
from .serializers import (
    CategorySerializer, CategoryListSerializer, SearchQuerySerializer,
    PopularSearchSerializer, SearchSuggestionSerializer, SavedSearchSerializer
)


class SearchPagination(PageNumberPagination):
    """Custom pagination for search-related views"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryListView(generics.ListAPIView):
    """List job categories with hierarchy"""
    serializer_class = CategoryListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = SearchPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['parent', 'level', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'order', 'job_count', 'created_at']
    ordering = ['level', 'order', 'name']
    
    def get_queryset(self):
        """Get active categories with job counts"""
        return Category.objects.filter(is_active=True).annotate(
            job_count=Count('job_set', filter=Q(job_set__status='published'))
        )
    
    def list(self, request, *args, **kwargs):
        """Enhanced list with category tree structure"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Check if tree structure requested
        tree_view = request.query_params.get('tree', 'false').lower() == 'true'
        
        if tree_view:
            # Build category tree
            categories = list(queryset)
            tree = self._build_category_tree(categories)
            return Response({
                'tree': tree,
                'total_categories': len(categories)
            })
        
        # Regular paginated list
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def _build_category_tree(self, categories):
        """Build hierarchical category tree"""
        category_dict = {cat.id: {
            'category': CategoryListSerializer(cat).data,
            'children': []
        } for cat in categories}
        
        tree = []
        
        for cat in categories:
            if cat.parent_id and cat.parent_id in category_dict:
                category_dict[cat.parent_id]['children'].append(category_dict[cat.id])
            else:
                tree.append(category_dict[cat.id])
        
        return tree


class CategoryDetailView(generics.RetrieveAPIView):
    """Get category details with subcategories"""
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        """Get active categories"""
        return Category.objects.filter(is_active=True)
    
    def retrieve(self, request, *args, **kwargs):
        """Get category with subcategories and related data"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Get subcategories
        subcategories = Category.objects.filter(
            parent=instance,
            is_active=True
        ).annotate(
            job_count=Count('job_set', filter=Q(job_set__status='published'))
        ).order_by('order', 'name')
        
        subcategory_serializer = CategoryListSerializer(subcategories, many=True)
        
        return Response({
            'category': serializer.data,
            'subcategories': subcategory_serializer.data,
            'total_jobs': getattr(instance, 'job_count', 0)
        })


class SearchQueryListCreateView(generics.ListCreateAPIView):
    """List and create search queries (for analytics)"""
    serializer_class = SearchQuerySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SearchPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['search_type', 'category', 'location', 'has_results']
    ordering = ['-searched_at']
    
    def get_queryset(self):
        """Get search queries for authenticated user"""
        return SearchQuery.objects.filter(user=self.request.user).select_related(
            'category', 'location'
        )
    
    def perform_create(self, serializer):
        """Create search query with user and IP info"""
        serializer.save(
            user=self.request.user,
            ip_address=self._get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            normalized_query=self._normalize_query(serializer.validated_data.get('query_text', ''))
        )
    
    def _get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip
    
    def _normalize_query(self, query):
        """Normalize search query for analysis"""
        return query.lower().strip()


class PopularSearchListView(generics.ListAPIView):
    """List popular/trending searches"""
    serializer_class = PopularSearchSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = SearchPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_trending', 'is_suggested', 'primary_category', 'primary_location']
    ordering_fields = ['search_count', 'daily_count', 'weekly_count', 'monthly_count']
    ordering = ['-search_count']
    
    def get_queryset(self):
        """Get popular searches with filtering"""
        queryset = PopularSearch.objects.filter(is_suggested=True).select_related(
            'primary_category', 'primary_location'
        )
        
        # Filter by trending if requested
        trending_only = self.request.query_params.get('trending_only')
        if trending_only and trending_only.lower() == 'true':
            queryset = queryset.filter(is_trending=True)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Enhanced list with search statistics"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get search statistics
        stats = queryset.aggregate(
            total_searches=Count('id'),
            trending_searches=Count('id', filter=Q(is_trending=True)),
            total_search_volume=Count('search_count')
        )
        
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


class SearchSuggestionListView(generics.ListAPIView):
    """Get search suggestions"""
    serializer_class = SearchSuggestionSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['suggestion_type', 'category', 'location', 'is_active', 'is_featured']
    ordering = ['-weight', '-usage_count']
    
    def get_queryset(self):
        """Get active suggestions"""
        queryset = SearchSuggestion.objects.filter(is_active=True).select_related(
            'category', 'location'
        )
        
        # Filter by query if provided
        query = self.request.query_params.get('q', '').strip()
        if query:
            queryset = queryset.filter(text__icontains=query)
        
        # Limit results for performance
        return queryset[:20]
    
    def list(self, request, *args, **kwargs):
        """Get suggestions with query context"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        query = request.query_params.get('q', '').strip()
        
        return Response({
            'suggestions': serializer.data,
            'query': query,
            'total_found': len(serializer.data)
        })


class SavedSearchListCreateView(generics.ListCreateAPIView):
    """List and create saved searches"""
    serializer_class = SavedSearchSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = SearchPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['category', 'location', 'email_alerts', 'alert_frequency']
    ordering_fields = ['created_at', 'last_used', 'use_count']
    ordering = ['-last_used', '-created_at']
    
    def get_queryset(self):
        """Get saved searches for authenticated user"""
        return SavedSearch.objects.filter(user=self.request.user).select_related(
            'category', 'location'
        )
    
    def perform_create(self, serializer):
        """Create saved search for authenticated user"""
        serializer.save(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Create saved search with validation"""
        # Check limit (max 20 saved searches per user)
        existing_count = SavedSearch.objects.filter(user=request.user).count()
        if existing_count >= 20:
            return Response({
                'error': 'Maximum of 20 saved searches allowed per user'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        saved_search = serializer.save(user=request.user)
        
        return Response({
            'message': 'Search saved successfully',
            'saved_search': SavedSearchSerializer(saved_search).data
        }, status=status.HTTP_201_CREATED)


class SavedSearchDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete saved search"""
    serializer_class = SavedSearchSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get saved searches for authenticated user"""
        return SavedSearch.objects.filter(user=self.request.user)
    
    def update(self, request, *args, **kwargs):
        """Update saved search and track usage"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Update last_used when search parameters are modified
        if any(field in request.data for field in ['query_text', 'additional_filters']):
            instance.last_used = timezone.now()
            instance.use_count = F('use_count') + 1
        
        saved_search = serializer.save()
        saved_search.refresh_from_db()  # Refresh to get updated use_count
        
        return Response({
            'message': 'Saved search updated successfully',
            'saved_search': SavedSearchSerializer(saved_search).data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete saved search"""
        instance = self.get_object()
        instance.delete()
        
        return Response({
            'message': 'Saved search deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def search_autocomplete(request):
    """Get search autocomplete suggestions"""
    query = request.query_params.get('q', '').strip()
    if not query or len(query) < 2:
        return Response({
            'suggestions': []
        })
    
    suggestions = []
    
    # Get category suggestions
    categories = Category.objects.filter(
        name__icontains=query,
        is_active=True
    )[:5]
    
    for cat in categories:
        suggestions.append({
            'text': cat.name,
            'type': 'category',
            'icon': cat.icon,
            'job_count': getattr(cat, 'job_count', 0)
        })
    
    # Get popular search suggestions
    popular = PopularSearch.objects.filter(
        query_text__icontains=query,
        is_suggested=True
    )[:5]
    
    for pop in popular:
        suggestions.append({
            'text': pop.query_text,
            'type': 'popular',
            'search_count': pop.search_count,
            'is_trending': pop.is_trending
        })
    
    # Get location suggestions (if apps.map is available)
    try:
        from apps.map.models import Location
        locations = Location.objects.filter(
            Q(name__icontains=query) | Q(city__icontains=query),
            is_verified=True
        )[:3]
        
        for loc in locations:
            suggestions.append({
                'text': f"{loc.name}, {loc.city}",
                'type': 'location',
                'coordinates': [loc.latitude, loc.longitude] if loc.coordinates else None
            })
    except ImportError:
        pass
    
    return Response({
        'suggestions': suggestions[:15],  # Limit total suggestions
        'query': query
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def track_search(request):
    """Track search query for analytics"""
    serializer = SearchQuerySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Create search query record
    search_query = SearchQuery.objects.create(
        user=request.user,
        query_text=request.data.get('query_text', ''),
        normalized_query=request.data.get('query_text', '').lower().strip(),
        search_type=request.data.get('search_type', 'job_search'),
        category_id=request.data.get('category'),
        location_id=request.data.get('location'),
        job_type=request.data.get('job_type', ''),
        experience_level=request.data.get('experience_level', ''),
        salary_min=request.data.get('salary_min'),
        salary_max=request.data.get('salary_max'),
        is_remote=request.data.get('is_remote'),
        results_count=request.data.get('results_count', 0),
        has_results=request.data.get('results_count', 0) > 0,
        ip_address=request.META.get('REMOTE_ADDR', ''),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        referrer=request.META.get('HTTP_REFERER', '')
    )
    
    # Update popular search if applicable
    query_text = request.data.get('query_text', '').strip()
    if query_text:
        popular_search, created = PopularSearch.objects.get_or_create(
            query_text=query_text,
            defaults={
                'search_count': 0,
                'daily_count': 0,
                'weekly_count': 0,
                'monthly_count': 0
            }
        )
        
        # Increment counters
        popular_search.search_count = F('search_count') + 1
        popular_search.daily_count = F('daily_count') + 1
        popular_search.weekly_count = F('weekly_count') + 1
        popular_search.monthly_count = F('monthly_count') + 1
        popular_search.last_searched = timezone.now()
        popular_search.save()
    
    return Response({
        'message': 'Search tracked successfully',
        'search_id': search_query.id
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def use_saved_search(request, search_id):
    """Use a saved search (increment usage counter)"""
    try:
        saved_search = SavedSearch.objects.get(
            id=search_id,
            user=request.user
        )
        
        # Update usage tracking
        saved_search.last_used = timezone.now()
        saved_search.use_count = F('use_count') + 1
        saved_search.save()
        saved_search.refresh_from_db()
        
        return Response({
            'message': 'Saved search used',
            'saved_search': SavedSearchSerializer(saved_search).data
        })
        
    except SavedSearch.DoesNotExist:
        return Response({
            'error': 'Saved search not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def search_trends(request):
    """Get search trends and popular categories"""
    # Get trending searches
    trending = PopularSearch.objects.filter(
        is_trending=True
    ).order_by('-daily_count')[:10]
    
    trending_serializer = PopularSearchSerializer(trending, many=True)
    
    # Get popular categories
    popular_categories = Category.objects.filter(
        is_active=True
    ).annotate(
        job_count=Count('job_set', filter=Q(job_set__status='published'))
    ).filter(job_count__gt=0).order_by('-job_count')[:10]
    
    category_serializer = CategoryListSerializer(popular_categories, many=True)
    
    return Response({
        'trending_searches': trending_serializer.data,
        'popular_categories': category_serializer.data,
        'generated_at': timezone.now()
    })
