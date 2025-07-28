from rest_framework import generics, status, permissions, parsers
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count
from .models import MediaFile, MediaFolder, MediaFileFolder, DownloadLog
from .serializers import (
    MediaFileSerializer, MediaFileListSerializer, MediaFileUploadSerializer,
    MediaFolderSerializer, MediaFileFolderSerializer, DownloadLogSerializer
)


class MediaPagination(PageNumberPagination):
    """Custom pagination for media views"""
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsOwnerOrPublic(permissions.BasePermission):
    """Custom permission for media files - owner or public files"""
    
    def has_object_permission(self, request, view, obj):
        # Public files are accessible to everyone
        if hasattr(obj, 'is_public') and obj.is_public and obj.is_approved:
            return True
        
        # Owner can access their own files
        if hasattr(obj, 'uploaded_by'):
            return obj.uploaded_by == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        
        return False


class MediaFileListCreateView(generics.ListCreateAPIView):
    """List and upload media files"""
    pagination_class = MediaPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['file_type', 'is_public', 'is_approved', 'is_temporary']
    ordering = ['-uploaded_at']
    parser_classes = [parsers.MultiPartParser, parsers.JSONParser]
    
    def get_serializer_class(self):
        """Use different serializers for list and upload"""
        if self.request.method == 'POST':
            return MediaFileUploadSerializer
        return MediaFileListSerializer
    
    def get_permissions(self):
        """Different permissions for list vs upload"""
        if self.request.method == 'POST':
            permission_classes = [permissions.IsAuthenticated]
        else:
            permission_classes = [permissions.IsAuthenticatedOrReadOnly]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Get accessible media files"""
        user = self.request.user
        
        if user.is_authenticated:
            # Authenticated users see their own files + public approved files
            return MediaFile.objects.filter(
                Q(uploaded_by=user) | Q(is_public=True, is_approved=True)
            ).select_related('uploaded_by')
        else:
            # Anonymous users only see public approved files
            return MediaFile.objects.filter(
                is_public=True,
                is_approved=True
            ).select_related('uploaded_by')
    
    def list(self, request, *args, **kwargs):
        """Enhanced list with media statistics"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get media statistics
        stats = {
            'total_files': queryset.count(),
            'total_size': sum(f.file_size for f in queryset if f.file_size),
            'file_types': queryset.values('file_type').annotate(
                count=Count('id')
            ).order_by('-count')
        }
        
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
    
    def create(self, request, *args, **kwargs):
        """Upload media file with validation"""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        media_file = serializer.save()
        
        # Return full media file data
        response_serializer = MediaFileSerializer(media_file)
        
        return Response({
            'message': 'File uploaded successfully',
            'file': response_serializer.data
        }, status=status.HTTP_201_CREATED)


class MediaFileDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete media file"""
    serializer_class = MediaFileSerializer
    permission_classes = [IsOwnerOrPublic]
    
    def get_queryset(self):
        """Get accessible media files"""
        user = self.request.user
        
        if user.is_authenticated:
            return MediaFile.objects.filter(
                Q(uploaded_by=user) | Q(is_public=True, is_approved=True)
            ).select_related('uploaded_by')
        else:
            return MediaFile.objects.filter(
                is_public=True,
                is_approved=True
            ).select_related('uploaded_by')
    
    def retrieve(self, request, *args, **kwargs):
        """Get media file with download tracking"""
        instance = self.get_object()
        
        # Track access if different user
        if request.user.is_authenticated and request.user != instance.uploaded_by:
            instance.last_accessed = timezone.now()
            instance.save(update_fields=['last_accessed'])
        
        serializer = self.get_serializer(instance)
        
        return Response({
            'file': serializer.data,
            'can_edit': (
                request.user.is_authenticated and 
                instance.uploaded_by == request.user
            ),
            'can_download': True  # All accessible files can be downloaded
        })
    
    def update(self, request, *args, **kwargs):
        """Update media file metadata (owner only)"""
        instance = self.get_object()
        
        if instance.uploaded_by != request.user:
            return Response({
                'error': 'You can only edit files you uploaded'
            }, status=status.HTTP_403_FORBIDDEN)
        
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        media_file = serializer.save()
        
        return Response({
            'message': 'File updated successfully',
            'file': serializer.data
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete media file (owner only)"""
        instance = self.get_object()
        
        if instance.uploaded_by != request.user:
            return Response({
                'error': 'You can only delete files you uploaded'
            }, status=status.HTTP_403_FORBIDDEN)
        
        instance.delete()  # This will also delete the physical file
        
        return Response({
            'message': 'File deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


class MediaFolderListCreateView(generics.ListCreateAPIView):
    """List and create media folders"""
    serializer_class = MediaFolderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MediaPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['parent', 'is_public']
    ordering = ['name']
    
    def get_queryset(self):
        """Get folders for authenticated user"""
        return MediaFolder.objects.filter(
            owner=self.request.user
        ).select_related('parent', 'owner')
    
    def perform_create(self, serializer):
        """Create folder for authenticated user"""
        serializer.save(owner=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """Create folder with validation"""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        folder = serializer.save()
        
        return Response({
            'message': 'Folder created successfully',
            'folder': MediaFolderSerializer(folder).data
        }, status=status.HTTP_201_CREATED)


class MediaFolderDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete media folder"""
    serializer_class = MediaFolderSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get folders for authenticated user"""
        return MediaFolder.objects.filter(owner=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        """Get folder with its files"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Get files in this folder
        folder_files = MediaFileFolder.objects.filter(
            folder=instance
        ).select_related('file')[:20]  # Limit to first 20 files
        
        file_serializer = MediaFileFolderSerializer(folder_files, many=True)
        
        return Response({
            'folder': serializer.data,
            'files': file_serializer.data,
            'total_files': MediaFileFolder.objects.filter(folder=instance).count()
        })
    
    def destroy(self, request, *args, **kwargs):
        """Delete folder (must be empty)"""
        instance = self.get_object()
        
        # Check if folder has files
        if MediaFileFolder.objects.filter(folder=instance).exists():
            return Response({
                'error': 'Cannot delete folder that contains files'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if folder has subfolders
        if MediaFolder.objects.filter(parent=instance).exists():
            return Response({
                'error': 'Cannot delete folder that contains subfolders'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        instance.delete()
        
        return Response({
            'message': 'Folder deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([IsOwnerOrPublic])
def download_file(request, file_id):
    """Download media file with tracking"""
    try:
        media_file = MediaFile.objects.get(id=file_id)
        
        # Check permissions
        if not media_file.is_public and media_file.uploaded_by != request.user:
            return Response({
                'error': 'Access denied'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Log download
        DownloadLog.objects.create(
            file=media_file,
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            referrer=request.META.get('HTTP_REFERER', ''),
            download_source='api',
            was_successful=True
        )
        
        # Increment download count
        media_file.download_count += 1
        media_file.last_accessed = timezone.now()
        media_file.save(update_fields=['download_count', 'last_accessed'])
        
        # Return file
        response = HttpResponse(media_file.file.read(), content_type=media_file.mime_type)
        response['Content-Disposition'] = f'attachment; filename="{media_file.original_filename}"'
        response['Content-Length'] = media_file.file_size
        
        return response
        
    except MediaFile.DoesNotExist:
        raise Http404("File not found")
    except Exception as e:
        # Log failed download
        try:
            DownloadLog.objects.create(
                file_id=file_id,
                user=request.user if request.user.is_authenticated else None,
                ip_address=request.META.get('REMOTE_ADDR', ''),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                download_source='api',
                was_successful=False,
                error_message=str(e)
            )
        except:
            pass
        
        return Response({
            'error': 'Download failed'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_file_to_folder(request):
    """Add file to folder"""
    file_id = request.data.get('file_id')
    folder_id = request.data.get('folder_id')
    
    if not file_id or not folder_id:
        return Response({
            'error': 'Both file_id and folder_id are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        media_file = MediaFile.objects.get(id=file_id, uploaded_by=request.user)
        folder = MediaFolder.objects.get(id=folder_id, owner=request.user)
        
        # Check if file is already in folder
        if MediaFileFolder.objects.filter(file=media_file, folder=folder).exists():
            return Response({
                'message': 'File is already in this folder'
            }, status=status.HTTP_200_OK)
        
        # Add file to folder
        MediaFileFolder.objects.create(file=media_file, folder=folder)
        
        return Response({
            'message': 'File added to folder successfully'
        })
        
    except MediaFile.DoesNotExist:
        return Response({
            'error': 'File not found or access denied'
        }, status=status.HTTP_404_NOT_FOUND)
    except MediaFolder.DoesNotExist:
        return Response({
            'error': 'Folder not found or access denied'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def remove_file_from_folder(request, file_id, folder_id):
    """Remove file from folder"""
    try:
        media_file = MediaFile.objects.get(id=file_id, uploaded_by=request.user)
        folder = MediaFolder.objects.get(id=folder_id, owner=request.user)
        
        file_folder = MediaFileFolder.objects.get(file=media_file, folder=folder)
        file_folder.delete()
        
        return Response({
            'message': 'File removed from folder successfully'
        })
        
    except (MediaFile.DoesNotExist, MediaFolder.DoesNotExist):
        return Response({
            'error': 'File or folder not found or access denied'
        }, status=status.HTTP_404_NOT_FOUND)
    except MediaFileFolder.DoesNotExist:
        return Response({
            'error': 'File is not in this folder'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_media_stats(request):
    """Get media statistics for authenticated user"""
    user = request.user
    
    files = MediaFile.objects.filter(uploaded_by=user)
    folders = MediaFolder.objects.filter(owner=user)
    
    # File statistics
    file_stats = files.aggregate(
        total_files=Count('id'),
        total_size=Count('file_size'),  # Sum would be better but Count is safer
        public_files=Count('id', filter=Q(is_public=True)),
        approved_files=Count('id', filter=Q(is_approved=True)),
        temporary_files=Count('id', filter=Q(is_temporary=True))
    )
    
    # File type breakdown
    file_types = files.values('file_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Download statistics
    total_downloads = sum(f.download_count for f in files)
    
    stats = {
        'files': file_stats,
        'folders': {
            'total_folders': folders.count(),
            'public_folders': folders.filter(is_public=True).count()
        },
        'file_types': list(file_types),
        'total_downloads': total_downloads,
        'storage_usage': {
            'total_files': file_stats['total_files'],
            'estimated_size_mb': sum(f.file_size for f in files if f.file_size) / (1024 * 1024)
        }
    }
    
    return Response(stats)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def cleanup_temporary_files(request):
    """Cleanup expired temporary files"""
    deleted_count, _ = MediaFile.objects.filter(
        uploaded_by=request.user,
        is_temporary=True,
        expires_at__lt=timezone.now()
    ).delete()
    
    return Response({
        'message': f'Cleaned up {deleted_count} expired temporary files',
        'deleted_count': deleted_count
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def download_history(request):
    """Get download history for user's files"""
    user_files = MediaFile.objects.filter(uploaded_by=request.user)
    
    downloads = DownloadLog.objects.filter(
        file__in=user_files
    ).select_related('file', 'user').order_by('-downloaded_at')[:50]
    
    serializer = DownloadLogSerializer(downloads, many=True)
    
    return Response({
        'downloads': serializer.data,
        'total_downloads': DownloadLog.objects.filter(file__in=user_files).count()
    })
