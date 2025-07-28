from django.contrib import admin
from .models import MediaFile, MediaFolder, MediaFileFolder, DownloadLog

@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ('original_filename', 'uploaded_by', 'file_type', 'uploaded_at')
    list_filter = ('file_type', 'is_public')
    search_fields = ('original_filename',)

@admin.register(MediaFolder)
class MediaFolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'is_public')
    list_filter = ('is_public',)

@admin.register(MediaFileFolder)
class MediaFileFolderAdmin(admin.ModelAdmin):
    list_display = ('folder', 'file')
    search_fields = ('folder__name', 'file__original_filename')

@admin.register(DownloadLog)
class DownloadLogAdmin(admin.ModelAdmin):
    list_display = ('file', 'user', 'downloaded_at', 'was_successful')
    list_filter = ('was_successful',)
