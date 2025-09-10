from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    github_username = models.CharField(max_length=255, blank=True)
    avatar_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    company = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, blank=True)
    blog = models.URLField(blank=True)
    html_url = models.URLField(blank=True)
    followers = models.IntegerField(default=0)
    following = models.IntegerField(default=0)
    public_repos = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Profile<{self.user.username}>"


class UserPreferences(models.Model):
    THEME_LIGHT = "light"
    THEME_DARK = "dark"
    THEME_CHOICES = [
        (THEME_LIGHT, "Light"),
        (THEME_DARK, "Dark"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    theme = models.CharField(max_length=16, choices=THEME_CHOICES, default=THEME_LIGHT)
    primary_color = models.CharField(max_length=7, default="#4f46e5")
    accent_color = models.CharField(max_length=7, default="#22c55e")
    bio_intro = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"Preferences<{self.user.username}>"
