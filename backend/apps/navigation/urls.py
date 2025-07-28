from django.urls import path
from . import views

app_name = 'navigation'

urlpatterns = [
    # Main navigation
    path('menu/', views.main_navigation, name='main_navigation'),
    path('breadcrumbs/', views.breadcrumbs, name='breadcrumbs'),
    path('quick-actions/', views.quick_actions, name='quick_actions'),
    
    # User-specific navigation
    path('stats/', views.user_navigation_stats, name='user_navigation_stats'),
    
    # SEO and sitemap
    path('sitemap/', views.sitemap_data, name='sitemap_data'),
] 