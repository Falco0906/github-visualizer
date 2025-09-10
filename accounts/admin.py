from django.contrib import admin
from .models import UserProfile, UserPreferences


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "github_username", "followers", "following", "public_repos", "updated_at")
    search_fields = ("user__username", "github_username")


@admin.register(UserPreferences)
class UserPreferencesAdmin(admin.ModelAdmin):
    list_display = ("user", "theme", "primary_color", "accent_color")
    search_fields = ("user__username",)
