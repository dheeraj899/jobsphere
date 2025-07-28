from django.db import models
from django.contrib.auth.models import User
import os


class MediaFile(models.Model):
    """File uploads for various purposes (avatars, resumes, documents, etc.)"""
    FILE_TYPES = [
        ('image', 'Image'),
        ('document', 'Document'),
        ('resume', 'Resume'),
        ('portfolio', 'Portfolio'),
        ('avatar', 'Avatar'),
        ('company_logo', 'Company Logo'),
        ('attachment', 'Attachment'),
        ('other', 'Other'),
    ]
    
    # Core file info
    file = models.FileField(upload_to='uploads/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255, db_index=True)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, db_index=True)
    
    # File metadata
    file_size = models.PositiveIntegerField(help_text="File size in bytes", db_index=True)
    mime_type = models.CharField(max_length=100, db_index=True)
    file_extension = models.CharField(max_length=10, db_index=True)
    
    # Image-specific fields
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    
    # Ownership and usage
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='uploaded_files',
        db_index=True
    )
    
    # Usage context (generic foreign key alternative)
    related_object_type = models.CharField(max_length=50, blank=True, db_index=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    
    # Status
    is_public = models.BooleanField(default=False, db_index=True)
    is_approved = models.BooleanField(default=True, db_index=True)  # For moderation
    is_temporary = models.BooleanField(default=False, db_index=True)  # For cleanup
    
    # Security
    access_token = models.CharField(max_length=64, blank=True, db_index=True)  # For secure access
    download_count = models.PositiveIntegerField(default=0)
    
    # SEO and metadata
    alt_text = models.CharField(max_length=255, blank=True)
    caption = models.TextField(blank=True)
    title = models.CharField(max_length=200, blank=True)
    
    # Storage info
    storage_path = models.CharField(max_length=500, blank=True)
    checksum = models.CharField(max_length=64, blank=True, db_index=True)  # For duplicate detection
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_accessed = models.DateTimeField(null=True, blank=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)  # For temporary files
    
    class Meta:
        db_table = 'media_files'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['uploaded_by', '-uploaded_at']),
            models.Index(fields=['file_type', 'is_public']),
            models.Index(fields=['related_object_type', 'related_object_id']),
            models.Index(fields=['is_temporary', 'expires_at']),
            models.Index(fields=['mime_type', 'file_size']),
            models.Index(fields=['checksum']),  # For duplicate detection
        ]
    
    def __str__(self):
        return f"{self.original_filename} ({self.file_type})"
    
    @property
    def file_size_formatted(self):
        """Return human-readable file size"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    @property 
    def is_image(self):
        """Check if file is an image"""
        return self.mime_type.startswith('image/')
    
    @property
    def file_url(self):
        """Return the file URL"""
        if self.file:
            return self.file.url
        return None
    
    def delete(self, *args, **kwargs):
        """Override delete to remove file from storage"""
        if self.file:
            # Delete the actual file
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)


class MediaFolder(models.Model):
    """Organize media files into folders"""
    name = models.CharField(max_length=100, db_index=True)
    slug = models.SlugField(max_length=100, db_index=True)
    description = models.TextField(blank=True)
    
    # Hierarchy
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='subfolders',
        db_index=True
    )
    
    # Ownership
    owner = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='media_folders',
        db_index=True
    )
    
    # Settings
    is_public = models.BooleanField(default=False, db_index=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'media_folders'
        unique_together = [['owner', 'slug', 'parent']]
        ordering = ['name']
        indexes = [
            models.Index(fields=['owner', 'is_public']),
            models.Index(fields=['parent', 'name']),
        ]
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name}/{self.name}"
        return self.name


class MediaFileFolder(models.Model):
    """Many-to-many relationship between files and folders"""
    file = models.ForeignKey(
        MediaFile, 
        on_delete=models.CASCADE,
        db_index=True
    )
    folder = models.ForeignKey(
        MediaFolder, 
        on_delete=models.CASCADE,
        db_index=True
    )
    
    # Timestamps
    added_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'media_file_folders'
        unique_together = [['file', 'folder']]
        indexes = [
            models.Index(fields=['folder', '-added_at']),
            models.Index(fields=['file', '-added_at']),
        ]
    
    def __str__(self):
        return f"{self.file.original_filename} in {self.folder.name}"


class DownloadLog(models.Model):
    """Track file downloads for analytics and security"""
    file = models.ForeignKey(
        MediaFile, 
        on_delete=models.CASCADE, 
        related_name='downloads',
        db_index=True
    )
    
    # Download info
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        db_index=True
    )
    ip_address = models.GenericIPAddressField(db_index=True)
    user_agent = models.TextField(blank=True)
    
    # Context
    referrer = models.URLField(blank=True)
    download_source = models.CharField(
        max_length=50,
        choices=[
            ('direct', 'Direct Link'),
            ('profile', 'Profile Page'),
            ('job_application', 'Job Application'),
            ('message', 'Message Attachment'),
            ('api', 'API'),
        ],
        blank=True,
        db_index=True
    )
    
    # Success tracking
    was_successful = models.BooleanField(default=True, db_index=True)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    downloaded_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'download_logs'
        ordering = ['-downloaded_at']
        indexes = [
            models.Index(fields=['file', '-downloaded_at']),
            models.Index(fields=['user', '-downloaded_at']),
            models.Index(fields=['ip_address', '-downloaded_at']),
            models.Index(fields=['download_source', '-downloaded_at']),
            models.Index(fields=['was_successful']),
        ]
    
    def __str__(self):
        user_info = self.user.username if self.user else self.ip_address
        return f"{user_info} downloaded {self.file.original_filename}"
