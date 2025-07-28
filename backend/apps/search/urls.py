from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category_detail'),
    
    # Search queries and tracking
    path('queries/', views.SearchQueryListCreateView.as_view(), name='search_query_list_create'),
    path('track/', views.track_search, name='track_search'),
    
    # Popular searches and suggestions
    path('popular/', views.PopularSearchListView.as_view(), name='popular_search_list'),
    path('suggestions/', views.SearchSuggestionListView.as_view(), name='search_suggestion_list'),
    path('autocomplete/', views.search_autocomplete, name='search_autocomplete'),
    path('trends/', views.search_trends, name='search_trends'),
    
    # Saved searches
    path('saved/', views.SavedSearchListCreateView.as_view(), name='saved_search_list_create'),
    path('saved/<int:pk>/', views.SavedSearchDetailView.as_view(), name='saved_search_detail'),
    path('saved/<int:search_id>/use/', views.use_saved_search, name='use_saved_search'),
] 