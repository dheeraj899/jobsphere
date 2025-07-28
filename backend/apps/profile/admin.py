from django.contrib import admin
from .models import UserProfile, Experience, About, Contact

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'is_active', 'created_at')
    list_filter = ('is_active', 'location')
    search_fields = ('user__username', 'user__email')

class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 0

@admin.register(About)
class AboutAdmin(admin.ModelAdmin):
    list_display = ('user', 'years_of_experience')
    search_fields = ('user__username',)

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('user', 'primary_email', 'city', 'country')
    search_fields = ('user__username', 'primary_email') 