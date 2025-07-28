from django.urls import path
from . import views

app_name = 'profile'

urlpatterns = [
    # User profile
    path('', views.UserProfileView.as_view(), name='user_profile'),
    path('public/<str:username>/', views.PublicProfileView.as_view(), name='public_profile'),
    path('stats/', views.profile_stats, name='profile_stats'),
    path('avatar/upload/', views.upload_avatar, name='upload_avatar'),
    
    # Experience management
    path('experience/', views.ExperienceListCreateView.as_view(), name='experience_list_create'),
    path('experience/<int:pk>/', views.ExperienceDetailView.as_view(), name='experience_detail'),
    
    # About section
    path('about/', views.AboutView.as_view(), name='about'),
    
    # Contact information
    path('contact/', views.ContactView.as_view(), name='contact'),
] 