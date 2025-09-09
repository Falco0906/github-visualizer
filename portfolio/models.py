from django.conf import settings
from django.db import models


class GitHubSnapshot(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    raw_profile = models.JSONField(default=dict)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fetched_at"]


class Repository(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    repo_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    html_url = models.URLField()
    stargazers_count = models.IntegerField(default=0)
    forks_count = models.IntegerField(default=0)
    language_primary = models.CharField(max_length=64, blank=True)
    languages = models.JSONField(default=dict, blank=True)
    topics = models.JSONField(default=list, blank=True)
    pushed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    is_pinned = models.BooleanField(default=False)

    class Meta:
        ordering = ["-stargazers_count", "name"]

    def __str__(self) -> str:
        return self.full_name


class CommitActivity(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE, related_name="activities")
    week = models.DateField()
    commits = models.IntegerField(default=0)

    class Meta:
        unique_together = ("repo", "week")
        ordering = ["-week"]


class PortfolioHighlight(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    repo = models.ForeignKey(Repository, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True)
    blurb = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
