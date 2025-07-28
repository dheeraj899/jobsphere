from django.urls import path
from . import views

app_name = 'media'

urlpatterns = [
    # Media files
    path('files/', views.MediaFileListCreateView.as_view(), name='media_file_list_create'),
    path('files/<int:pk>/', views.MediaFileDetailView.as_view(), name='media_file_detail'),
    path('files/<int:file_id>/download/', views.download_file, name='download_file'),
    path('files/stats/', views.my_media_stats, name='my_media_stats'),
    path('files/cleanup/', views.cleanup_temporary_files, name='cleanup_temporary_files'),
    
    # Media folders
    path('folders/', views.MediaFolderListCreateView.as_view(), name='media_folder_list_create'),
    path('folders/<int:pk>/', views.MediaFolderDetailView.as_view(), name='media_folder_detail'),
    
    # Folder management
    path('folders/add-file/', views.add_file_to_folder, name='add_file_to_folder'),
    path('folders/<int:folder_id>/files/<int:file_id>/remove/', views.remove_file_from_folder, name='remove_file_from_folder'),
    
    # Download tracking
    path('downloads/history/', views.download_history, name='download_history'),
] 