from django.contrib import admin
from .models import GitHubSnapshot, Repository, CommitActivity, PortfolioHighlight


@admin.register(GitHubSnapshot)
class GitHubSnapshotAdmin(admin.ModelAdmin):
    list_display = ("user", "fetched_at")


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ("full_name", "owner", "stargazers_count", "forks_count", "is_pinned")
    search_fields = ("full_name", "name", "owner__username")


@admin.register(CommitActivity)
class CommitActivityAdmin(admin.ModelAdmin):
    list_display = ("repo", "week", "commits")


@admin.register(PortfolioHighlight)
class PortfolioHighlightAdmin(admin.ModelAdmin):
    list_display = ("user", "repo", "order")
    ordering = ("user", "order")
