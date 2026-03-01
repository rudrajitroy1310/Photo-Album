from django.contrib import admin
from .models import Album, Photo

class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 1
    # 'uploaded_by' is now visible when viewing an Album
    fields = ('image', 'caption', 'uploaded_by')

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    # Display more info in the Album list view
    list_display = ('title', 'created_at', 'photo_count')
    inlines = [PhotoInline]

    def photo_count(self, obj):
        return obj.photos.count()
    photo_count.short_description = 'Number of Photos'

@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    # This helps you track which normal user uploaded which image
    list_display = ('album', 'uploaded_by', 'created_at')
    # Filter by user or album on the right sidebar
    list_filter = ('uploaded_by', 'album', 'created_at')
    # Search by caption or username
    search_fields = ('caption', 'uploaded_by__username')