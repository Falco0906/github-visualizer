from __future__ import annotations
import datetime
import logging
import os
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from accounts.models import UserProfile
from portfolio.models import GitHubSnapshot, Repository, CommitActivity

logger = logging.getLogger(__name__)


class GitHubClient:
    API_BASE = "https://api.github.com"

    def __init__(self, access_token: Optional[str] = None) -> None:
        self.session = requests.Session()
        # Always use the dedicated API token from settings, ignore passed token
        if settings.GITHUB_API_TOKEN:
            self.session.headers.update({"Authorization": f"token {settings.GITHUB_API_TOKEN}"})
        self.session.headers.update({"Accept": "application/vnd.github+json"})

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        resp = self.session.get(f"{self.API_BASE}{path}", params=params, timeout=20)
        
        # Always check rate limit info
        from .rate_limit import RateLimitInfo
        rate_info = RateLimitInfo.from_response(resp)
        
        # Handle rate limiting
        if resp.status_code == 403 and rate_info.is_exceeded():
            reset_seconds = rate_info.get_reset_seconds()
            raise Exception(f"GitHub API rate limit exceeded. Resets in {reset_seconds} seconds. "
                          f"Using {rate_info.used}/{rate_info.limit} requests.")
        
        resp.raise_for_status()
        return resp.json()

    def get_user(self) -> Dict[str, Any]:
        return self.get("/user")

    def get_public_user(self, username: str) -> Dict[str, Any]:
        return self.get(f"/users/{username}")

    def get_public_repos(self, username: str) -> List[Dict[str, Any]]:
        return self.get(f"/users/{username}/repos", params={"per_page": 100, "sort": "updated"})

    def get_pinned_repos(self, username: str) -> List[Dict[str, Any]]:
        # GitHub REST v3 does not directly expose pinned repos; using a fallback via stars/popularity
        repos = self.get(f"/users/{username}/repos", params={"sort": "pushed", "direction": "desc", "per_page": 100})
        return sorted(repos, key=lambda r: (r.get("stargazers_count", 0), r.get("forks_count", 0)), reverse=True)[:6]

    def get_repo_languages(self, owner: str, repo: str) -> Dict[str, int]:
        return self.get(f"/repos/{owner}/{repo}/languages")

    def get_commit_activity(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        # Returns last year of commit activity, weekly buckets
        return self.get(f"/repos/{owner}/{repo}/stats/commit_activity")

    def get_contributions(self, username: str) -> Dict[str, Any]:
        """Get user's contribution data for the contribution graph"""
        try:
            # Using the events API to simulate contribution data
            events = self.get(f"/users/{username}/events/public", params={"per_page": 100})
            
            # Create a contribution calendar
            today = datetime.datetime.now(datetime.timezone.utc)
            year_ago = today - datetime.timedelta(days=365)
            
            # Initialize contribution weeks
            weeks = []
            current_week = []
            current_date = year_ago
            
            while current_date <= today:
                # Count contributions for this day
                day_contributions = len([
                    e for e in events
                    if e.get("created_at", "").startswith(current_date.strftime("%Y-%m-%d"))
                ])
                
                # Calculate contribution level (0-3)
                if day_contributions == 0:
                    level = 0
                elif day_contributions <= 3:
                    level = 1
                elif day_contributions <= 6:
                    level = 2
                else:
                    level = 3
                
                # Add day to current week
                current_week.append({
                    "date": current_date.strftime("%Y-%m-%d"),
                    "count": day_contributions,
                    "level": level
                })
                
                # If week is complete (7 days) or we've reached today
                if len(current_week) == 7 or current_date == today:
                    # Pad the last week if needed
                    while len(current_week) < 7:
                        next_date = current_date + datetime.timedelta(days=1)
                        current_week.append({
                            "date": next_date.strftime("%Y-%m-%d"),
                            "count": 0,
                            "level": 0
                        })
                    
                    weeks.append({"days": current_week})
                    current_week = []
                
                current_date += datetime.timedelta(days=1)
            
            return {
                "contribution_weeks": weeks,
                "total_contributions": sum(e.get("count", 0) for w in weeks for e in w["days"]),
                "current_streak": 0,  # Calculate if needed
                "longest_streak": 0,  # Calculate if needed
            }
        except Exception as e:
            logger.error(f"Error fetching contributions for {username}: {str(e)}")
            # Return empty data structure
            return {
                "contribution_weeks": [{"days": [{"date": "", "count": 0, "level": 0} for _ in range(7)]} for _ in range(52)],
                "total_contributions": 0,
                "current_streak": 0,
                "longest_streak": 0,
            }

    def get_user_stats(self, username: str) -> Dict[str, Any]:
        """Get comprehensive user statistics for recruiters"""
        try:
            user_data = self.get_public_user(username)
            repos = self.get_public_repos(username)
            
            # Calculate aggregated stats
            total_stars = 0
            total_forks = 0
            languages = {}
            language_bytes = {}
            recent_repos = []
            
            for repo in repos:
                # Sum up stars and forks
                total_stars += int(repo.get("stargazers_count", 0))
                total_forks += int(repo.get("forks_count", 0))
                
                # Track languages
                lang = repo.get("language")
                if lang:
                    languages[lang] = languages.get(lang, 0) + 1
                    language_bytes[lang] = language_bytes.get(lang, 0) + int(repo.get("size", 0))
                
                # Check for recent activity
                if repo.get("updated_at"):
                    try:
                        updated_at = datetime.datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00"))
                        if (datetime.datetime.now(datetime.timezone.utc) - updated_at).days < 90:
                            recent_repos.append(repo)
                    except (ValueError, TypeError):
                        continue
            
            # These fields will be removed from display
            skill_level = ""
            activity_level = ""
            
            # Project diversity
            project_types = set()
            for repo in repos:
                if "web" in repo.get("name", "").lower() or "frontend" in repo.get("description", "").lower():
                    project_types.add("Frontend")
                if "api" in repo.get("name", "").lower() or "backend" in repo.get("description", "").lower():
                    project_types.add("Backend")
                if "mobile" in repo.get("name", "").lower() or "app" in repo.get("name", "").lower():
                    project_types.add("Mobile")
                if "ml" in repo.get("name", "").lower() or "ai" in repo.get("name", "").lower():
                    project_types.add("AI/ML")
                if "data" in repo.get("name", "").lower():
                    project_types.add("Data Science")
            
            stats = {
                "total_stars_received": int(total_stars),
                "total_forks_received": int(total_forks),
                "repository_count": len(repos),
                "languages_count": len(languages),
                "recent_activity": len(recent_repos),
                "project_diversity": list(project_types),
                "top_languages": sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)[:5],
                "years_experience": 0
            }
            
            # Calculate scores
            if total_stars > 0 or total_forks > 0:
                stats["collaboration_score"] = min(100, int((total_forks * 2 + len([r for r in repos if r.get("forks_count", 0) > 0])) * 5))
                stats["innovation_score"] = min(100, int((total_stars + len([r for r in repos if r.get("stargazers_count", 0) > 10])) * 2))
                stats["consistency_score"] = min(100, int(len(recent_repos) * 10))
            else:
                stats["collaboration_score"] = 0
                stats["innovation_score"] = 0
                stats["consistency_score"] = 0
            
            # Calculate years of experience
            try:
                created_at = datetime.datetime.fromisoformat(user_data.get("created_at", "").replace("Z", "+00:00"))
                stats["years_experience"] = max(1, int((datetime.datetime.now(datetime.timezone.utc) - created_at).days // 365))
            except (ValueError, TypeError):
                stats["years_experience"] = 1
            
            return stats
        except Exception:
            return {}


class GitHubIngestService:
    def __init__(self, user: User, access_token: Optional[str] = None) -> None:
        self.user = user
        self.token = access_token or self._get_user_token()
        self.client = GitHubClient(self.token)

    def _get_user_token(self) -> Optional[str]:
        try:
            social = self.user.social_auth.get(provider="github")
            return social.extra_data.get("access_token")
        except Exception:
            return None

    def sync_all(self) -> None:
        if not self.token:
            return
        user_data = self.client.get_user()
        self._upsert_profile(user_data)
        GitHubSnapshot.objects.create(user=self.user, raw_profile=user_data)
        self._sync_repos(user_data.get("login"))

    def _upsert_profile(self, data: Dict[str, Any]) -> None:
        profile, _ = UserProfile.objects.get_or_create(user=self.user)
        profile.github_username = data.get("login") or ""
        profile.avatar_url = data.get("avatar_url") or ""
        profile.bio = data.get("bio") or ""
        profile.company = data.get("company") or ""
        profile.location = data.get("location") or ""
        profile.blog = data.get("blog") or ""
        profile.html_url = data.get("html_url") or ""
        profile.followers = data.get("followers") or 0
        profile.following = data.get("following") or 0
        profile.public_repos = data.get("public_repos") or 0
        profile.save()

    def _sync_repos(self, username: Optional[str]) -> None:
        if not username:
            return
        pinned = self.client.get_pinned_repos(username)
        for repo in pinned:
            self._upsert_repo(repo, is_pinned=True)

        # Fetch user's repos for broader stats
        repos = self.client.get(f"/users/{username}/repos", params={"per_page": 100, "sort": "updated"})
        for repo in repos:
            self._upsert_repo(repo, is_pinned=False)

    def _upsert_repo(self, data: Dict[str, Any], is_pinned: bool) -> None:
        repo_id = data.get("id")
        full_name = data.get("full_name")
        if not repo_id or not full_name:
            return
        owner_name, repo_name = full_name.split("/")
        languages = {}
        try:
            languages = self.client.get_repo_languages(owner_name, repo_name)
        except Exception:
            pass

        repo_obj, _ = Repository.objects.update_or_create(
            repo_id=repo_id,
            defaults={
                "owner": self.user,
                "name": data.get("name") or repo_name,
                "full_name": full_name,
                "description": data.get("description") or "",
                "html_url": data.get("html_url") or "",
                "stargazers_count": data.get("stargazers_count") or 0,
                "forks_count": data.get("forks_count") or 0,
                "language_primary": data.get("language") or "",
                "languages": languages or {},
                "topics": data.get("topics") or [],
                "pushed_at": self._parse_dt(data.get("pushed_at")),
                "updated_at": self._parse_dt(data.get("updated_at")),
                "is_pinned": is_pinned,
            },
        )

        # Commit activity
        try:
            activity = self.client.get_commit_activity(owner_name, repo_name)
            for week in activity:
                week_start = datetime.date.fromtimestamp(week.get("week", 0))
                commits = sum(week.get("days", [])) if isinstance(week.get("days"), list) else week.get("total", 0)
                CommitActivity.objects.update_or_create(
                    owner=self.user,
                    repo=repo_obj,
                    week=week_start,
                    defaults={"commits": commits or 0},
                )
        except Exception:
            logger.debug("Failed to fetch commit activity for %s", full_name)

    @staticmethod
    def _parse_dt(value: Optional[str]) -> Optional[datetime.datetime]:
        if not value:
            return None
        try:
            return datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            return None
