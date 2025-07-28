from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from django.utils import timezone
from .models import MediaFile, MediaFolder, MediaFileFolder, DownloadLog
import mimetypes
import os


class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user serializer for nested relationships"""
    class Meta:
        ref_name = 'MediaUserBasic'
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']
        read_only_fields = ['id', 'username']


class MediaFileSerializer(serializers.ModelSerializer):
    """Media file serializer with validation and computed fields"""
    uploaded_by = UserBasicSerializer(read_only=True)
    file_size_formatted = serializers.ReadOnlyField()
    is_image = serializers.ReadOnlyField()
    file_url = serializers.ReadOnlyField()
    upload_info = serializers.SerializerMethodField()
    security_info = serializers.SerializerMethodField()
    
    class Meta:
        model = MediaFile
        fields = [
            'id', 'file', 'original_filename', 'file_type', 'file_size',
            'mime_type', 'file_extension', 'width', 'height',
            'uploaded_by', 'related_object_type', 'related_object_id',
            'is_public', 'is_approved', 'is_temporary', 'access_token',
            'download_count', 'alt_text', 'caption', 'title',
            'storage_path', 'checksum', 'uploaded_at', 'last_accessed',
            'expires_at', 'file_size_formatted', 'is_image', 'file_url',
            'upload_info', 'security_info'
        ]
        read_only_fields = [
            'id', 'uploaded_by', 'file_size', 'mime_type', 'file_extension',
            'width', 'height', 'storage_path', 'checksum', 'uploaded_at',
            'last_accessed', 'download_count', 'file_size_formatted',
            'is_image', 'file_url', 'upload_info', 'security_info'
        ]
    
    def get_upload_info(self, obj):
        """Return upload information summary"""
        return {
            'uploaded_days_ago': (timezone.now() - obj.uploaded_at).days,
            'last_accessed_days_ago': (timezone.now() - obj.last_accessed).days if obj.last_accessed else None,
            'is_recently_uploaded': (timezone.now() - obj.uploaded_at).days <= 7,
            'is_frequently_downloaded': obj.download_count >= 10,
            'has_expiration': obj.expires_at is not None,
            'is_expired': obj.expires_at and timezone.now() > obj.expires_at if obj.expires_at else False
        }
    
    def get_security_info(self, obj):
        """Return security and access information"""
        return {
            'has_access_token': bool(obj.access_token),
            'is_publicly_accessible': obj.is_public and obj.is_approved,
            'requires_approval': not obj.is_approved,
            'is_temporary_file': obj.is_temporary,
            'access_level': 'public' if obj.is_public else 'protected' if obj.access_token else 'private'
        }
    
    def validate_file(self, value):
        """Validate uploaded file"""
        if not value:
            raise serializers.ValidationError("No file provided.")
        
        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 50MB.")
        
        # Check file type based on extension
        allowed_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.webp',  # Images
            '.pdf', '.doc', '.docx', '.txt', '.rtf',   # Documents
            '.zip', '.rar', '.7z',                     # Archives
            '.mp4', '.avi', '.mov', '.wmv',            # Videos (limited)
        ]
        
        file_extension = os.path.splitext(value.name)[1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(f"File type {file_extension} is not allowed.")
        
        return value
    
    def validate_file_type(self, value):
        """Validate file type choice"""
        valid_types = dict(MediaFile.FILE_TYPES).keys()
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid file type. Must be one of: {', '.join(valid_types)}")
        return value
    
    def validate_alt_text(self, value):
        """Validate alt text for images"""
        if value and len(value) > 255:
            raise serializers.ValidationError("Alt text cannot be longer than 255 characters.")
        return value
    
    def validate_expires_at(self, value):
        """Validate expiration date"""
        if value and value <= timezone.now():
            raise serializers.ValidationError("Expiration date must be in the future.")
        return value
    
    def create(self, validated_data):
        """Create media file with auto-populated metadata"""
        file_obj = validated_data['file']
        
        # Auto-populate metadata
        validated_data['original_filename'] = file_obj.name
        validated_data['file_size'] = file_obj.size
        validated_data['mime_type'] = mimetypes.guess_type(file_obj.name)[0] or 'application/octet-stream'
        validated_data['file_extension'] = os.path.splitext(file_obj.name)[1].lower()
        
        # Set uploaded_by from request context
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['uploaded_by'] = request.user
        
        return super().create(validated_data)


class MediaFileListSerializer(serializers.ModelSerializer):
    """Simplified serializer for media file lists"""
    uploaded_by = serializers.StringRelatedField()
    file_size_formatted = serializers.ReadOnlyField()
    is_image = serializers.ReadOnlyField()
    
    class Meta:
        model = MediaFile
        fields = [
            'id', 'original_filename', 'file_type', 'file_size_formatted',
            'mime_type', 'uploaded_by', 'is_public', 'is_approved',
            'download_count', 'uploaded_at', 'is_image'
        ]
        read_only_fields = ['id', 'file_size_formatted', 'mime_type', 'uploaded_at', 'is_image']


class MediaFolderSerializer(serializers.ModelSerializer):
    """Media folder serializer with hierarchy support"""
    owner = UserBasicSerializer(read_only=True)
    parent_name = serializers.SerializerMethodField()
    files_count = serializers.SerializerMethodField()
    subfolders_count = serializers.SerializerMethodField()
    folder_path = serializers.SerializerMethodField()
    
    class Meta:
        model = MediaFolder
        fields = [
            'id', 'name', 'slug', 'description', 'parent', 'parent_name',
            'owner', 'is_public', 'created_at', 'updated_at',
            'files_count', 'subfolders_count', 'folder_path'
        ]
        read_only_fields = [
            'id', 'slug', 'owner', 'created_at', 'updated_at',
            'parent_name', 'files_count', 'subfolders_count', 'folder_path'
        ]
    
    def get_parent_name(self, obj):
        """Return parent folder name"""
        return obj.parent.name if obj.parent else None
    
    def get_files_count(self, obj):
        """Return count of files in this folder"""
        return MediaFileFolder.objects.filter(folder=obj).count()
    
    def get_subfolders_count(self, obj):
        """Return count of subfolders"""
        return obj.subfolders.count()
    
    def get_folder_path(self, obj):
        """Return full folder path"""
        path_parts = []
        current = obj
        while current:
            path_parts.insert(0, current.name)
            current = current.parent
        return ' / '.join(path_parts)
    
    def validate_name(self, value):
        """Validate folder name"""
        if not value or not value.strip():
            raise serializers.ValidationError("Folder name cannot be empty.")
        if len(value) > 100:
            raise serializers.ValidationError("Folder name cannot be longer than 100 characters.")
        
        # Check for invalid characters
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            if char in value:
                raise serializers.ValidationError(f"Folder name cannot contain '{char}' character.")
        
        return value.strip()
    
    def create(self, validated_data):
        """Create folder with auto-generated slug and owner"""
        # Set owner from request context
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['owner'] = request.user
        
        # Auto-generate slug
        from django.utils.text import slugify
        validated_data['slug'] = slugify(validated_data['name'])
        
        return super().create(validated_data)


class MediaFileFolderSerializer(serializers.ModelSerializer):
    """Media file-folder relationship serializer"""
    file = MediaFileListSerializer(read_only=True)
    folder = MediaFolderSerializer(read_only=True)
    file_id = serializers.IntegerField(write_only=True)
    folder_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = MediaFileFolder
        fields = ['id', 'file', 'folder', 'file_id', 'folder_id', 'added_at']
        read_only_fields = ['id', 'added_at']
    
    def validate_file_id(self, value):
        """Validate file exists and user has access"""
        try:
            file_obj = MediaFile.objects.get(id=value)
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                # Check if user owns the file or has permission
                if file_obj.uploaded_by != request.user and not file_obj.is_public:
                    raise serializers.ValidationError("You don't have permission to access this file.")
            return value
        except MediaFile.DoesNotExist:
            raise serializers.ValidationError("File does not exist.")
    
    def validate_folder_id(self, value):
        """Validate folder exists and user has access"""
        try:
            folder_obj = MediaFolder.objects.get(id=value)
            request = self.context.get('request')
            if request and request.user.is_authenticated:
                # Check if user owns the folder
                if folder_obj.owner != request.user:
                    raise serializers.ValidationError("You don't have permission to access this folder.")
            return value
        except MediaFolder.DoesNotExist:
            raise serializers.ValidationError("Folder does not exist.")


class DownloadLogSerializer(serializers.ModelSerializer):
    """Download log serializer for tracking file access"""
    file = MediaFileListSerializer(read_only=True)
    user = UserBasicSerializer(read_only=True)
    download_context = serializers.SerializerMethodField()
    
    class Meta:
        model = DownloadLog
        fields = [
            'id', 'file', 'user', 'ip_address', 'user_agent',
            'referrer', 'download_source', 'was_successful',
            'error_message', 'downloaded_at', 'download_context'
        ]
        read_only_fields = [
            'id', 'file', 'user', 'ip_address', 'user_agent',
            'downloaded_at', 'download_context'
        ]
    
    def get_download_context(self, obj):
        """Return download context information"""
        return {
            'has_user': obj.user is not None,
            'is_successful': obj.was_successful,
            'has_error': bool(obj.error_message),
            'download_days_ago': (timezone.now() - obj.downloaded_at).days,
            'is_recent': (timezone.now() - obj.downloaded_at).days <= 1,
            'source_category': obj.download_source or 'unknown'
        }


class MediaFileUploadSerializer(serializers.ModelSerializer):
    """Simplified serializer for file uploads"""
    
    class Meta:
        model = MediaFile
        fields = [
            'file', 'file_type', 'alt_text', 'caption', 'title',
            'is_public', 'is_temporary', 'expires_at',
            'related_object_type', 'related_object_id'
        ]
    
    def validate_file(self, value):
        """Validate uploaded file"""
        if not value:
            raise serializers.ValidationError("No file provided.")
        
        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 50MB.")
        
        return value
    
    def create(self, validated_data):
        """Create media file with auto-populated metadata"""
        file_obj = validated_data['file']
        
        # Auto-populate metadata
        validated_data['original_filename'] = file_obj.name
        validated_data['file_size'] = file_obj.size
        validated_data['mime_type'] = mimetypes.guess_type(file_obj.name)[0] or 'application/octet-stream'
        validated_data['file_extension'] = os.path.splitext(file_obj.name)[1].lower()
        
        # Set uploaded_by from request context
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['uploaded_by'] = request.user
        
        return super().create(validated_data) 