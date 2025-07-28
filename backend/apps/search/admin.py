from django.contrib import admin
from .models import Category, SearchQuery, PopularSearch, SearchSuggestion, SavedSearch

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'is_active')
    list_filter = ('is_active', 'level')
    search_fields = ('name',)

@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ('user', 'query_text', 'searched_at', 'has_results')
    list_filter = ('has_results', 'search_type')

@admin.register(PopularSearch)
class PopularSearchAdmin(admin.ModelAdmin):
    list_display = ('query_text', 'search_count', 'is_trending')
    list_filter = ('is_trending',)

@admin.register(SearchSuggestion)
class SearchSuggestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'suggestion_type', 'usage_count', 'is_active')
    list_filter = ('suggestion_type', 'is_active')

@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'query_text', 'email_alerts')
    list_filter = ('email_alerts', 'alert_frequency')
