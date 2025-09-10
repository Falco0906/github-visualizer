import datetime
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST
import requests

from .models import PortfolioHighlight
from githubapi.services import GitHubClient

logger = logging.getLogger(__name__)


def public_portfolio(request, username: str):
    highlights = PortfolioHighlight.objects.filter(user__username=username).select_related("repo")
    return render(request, "public_portfolio.html", {"username": username, "highlights": highlights})


def search_redirect(request):
    q = request.GET.get("q", "").strip()
    if not q:
        return render(request, "error.html", {
            "error_title": "Invalid Search",
            "error_message": "Please enter a GitHub username to search.",
            "error_icon": "fa-search"
        })
    
    # GitHub usernames are case-insensitive, use as-is for the API call
    client = GitHubClient(access_token=None)
    try:
        # Try to verify the username exists first
        client.get_public_user(q)
        return redirect("public_viewer", username=q)
    except requests.exceptions.RequestException as e:
        if "rate limit exceeded" in str(e).lower():
            # Get rate limit info from the exception message
            import re
            reset_seconds = 0
            match = re.search(r"Resets in (\d+) seconds", str(e))
            if match:
                reset_seconds = int(match.group(1))
            
            return render(request, "rate_limit.html", {
                "reset_seconds": reset_seconds,
                "reset_minutes": reset_seconds // 60,
                "search_query": q
            })
        elif e.response and e.response.status_code == 404:
            return render(request, "error.html", {
                "error_title": "User Not Found",
                "error_message": f"Could not find GitHub user '{q}'. Please check the username and try again.",
                "error_icon": "fa-user-slash"
            })
        else:
            return render(request, "error.html", {
                "error_title": "GitHub API Error",
                "error_message": "An error occurred while fetching user data. Please try again.",
                "error_icon": "fa-exclamation-triangle"
            })


def public_viewer(request, username: str):
    try:
        # Initialize GitHub client which will use the dedicated token from settings
        client = GitHubClient()
        
        try:
            # Get basic profile info
            profile = client.get_public_user(username)
        except Exception as e:
            logger.error(f"Error fetching user profile: {str(e)}")
            # Provide default profile with required fields
            profile = {
                "login": username,
                "name": username,
                "avatar_url": "",
                "html_url": f"https://github.com/{username}",
                "followers": 0,
                "bio": None,
                "blog": None,
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            
        try:
            # Get repositories
            repos = client.get_public_repos(username)
            if not isinstance(repos, list):
                repos = []
        except Exception as e:
            logger.error(f"Error fetching repositories: {str(e)}")
            repos = []
            
        # Calculate basic stats safely using defensive programming
        try:
            total_stars = sum(int(repo.get("stargazers_count", 0)) for repo in repos if isinstance(repo, dict))
        except (TypeError, ValueError):
            total_stars = 0
            
        try:
            total_forks = sum(int(repo.get("forks_count", 0)) for repo in repos if isinstance(repo, dict))
        except (TypeError, ValueError):
            total_forks = 0
        
        # Get top repositories
        repos_top = sorted(repos, key=lambda r: (r.get("stargazers_count", 0), r.get("forks_count", 0)), reverse=True)[:8]
        
        # Calculate language stats
        languages = {}
        for repo in repos:
            lang = repo.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1
        
        # Count recent activity (last 90 days)
        recent_activity = sum(1 for repo in repos 
                            if repo.get("updated_at") and 
                            (datetime.datetime.now(datetime.timezone.utc) - 
                             datetime.datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00"))).days < 90)
        
        # Calculate recruiter insights
        # Project diversity based on repository names and descriptions
        project_types = set()
        for repo in repos:
            # Skip if repo is not a dict
            if not isinstance(repo, dict):
                continue
                
            try:
                name = (repo.get("name") or "").lower()
                description = (repo.get("description") or "").lower()
                
                # Keywords for different project types
                keywords = {
                    "Frontend": ["web", "frontend", "react", "vue", "angular"],
                    "Backend": ["api", "backend", "server", "django", "flask"],
                    "Mobile": ["mobile", "ios", "android", "flutter", "react-native"],
                    "AI/ML": ["ml", "ai", "tensorflow", "pytorch", "machine-learning"],
                    "Data": ["data", "analytics", "visualization", "dashboard"]
                }
                
                # Check for keywords in name and description
                for project_type, kw_list in keywords.items():
                    if any(kw in name or kw in description for kw in kw_list):
                        project_types.add(project_type)
            except (AttributeError, TypeError):
                continue

        # Calculate collaboration score (based on forks, PRs, and repo interactions)
        forked_repos = len([r for r in repos if r.get("forks_count", 0) > 0])
        collaboration_base = (total_forks * 2 + forked_repos * 5)
        collaboration_score = min(100, int(collaboration_base * 2))

        # Calculate innovation score (based on stars, unique languages, and project diversity)
        starred_repos = len([r for r in repos if r.get("stargazers_count", 0) > 0])
        innovation_base = (total_stars + starred_repos * 2 + len(languages) * 5 + len(project_types) * 10)
        innovation_score = min(100, int(innovation_base * 0.5))

        # Calculate consistency score (based on recent activity and commit frequency)
        recent_repos = len([r for r in repos 
                          if r.get("updated_at") and 
                          (datetime.datetime.now(datetime.timezone.utc) - 
                           datetime.datetime.fromisoformat(r["updated_at"].replace("Z", "+00:00"))).days < 90])
        consistency_score = min(100, int(recent_repos * 10))

        # Get contribution data
        try:
            contribution_data = client.get_contributions(username)
        except Exception as e:
            logger.error(f"Error fetching contribution data: {str(e)}")
            contribution_data = {
                "contribution_weeks": [{"days": [{"date": "", "count": 0, "level": 0} for _ in range(7)]} for _ in range(52)],
                "total_contributions": 0,
                "current_streak": 0,
                "longest_streak": 0,
            }

        # Calculate years of experience safely
        try:
            created_at = profile.get("created_at", "")
            if created_at:
                created_date = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                years_exp = max(1, int((datetime.datetime.now(datetime.timezone.utc) - created_date).days / 365))
            else:
                years_exp = 1
        except (ValueError, AttributeError, TypeError):
            years_exp = 1

        # Create stats dictionary with safe defaults
        user_stats = {
            "total_stars_received": total_stars or 0,
            "total_forks_received": total_forks or 0,
            "repository_count": len(repos),
            "languages_count": len(languages or {}),
            "recent_activity": recent_activity or 0,
            "project_diversity": sorted(list(project_types)) if project_types else [],
            "collaboration_score": collaboration_score or 0,
            "innovation_score": innovation_score or 0,
            "consistency_score": consistency_score or 0,
            "years_experience": years_exp
        }
        
        # Chart data
        star_labels = [r.get("name") for r in repos_top]
        star_values = [r.get("stargazers_count", 0) for r in repos_top]
        fork_labels = [r.get("name") for r in repos_top]
        fork_values = [r.get("forks_count", 0) for r in repos_top]
        lang_data = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:10]
        lang_labels = [item[0] for item in lang_data]
        lang_values = [item[1] for item in lang_data]
        
        # Extract social links from bio
        social_links = {}
        if profile.get("bio"):
            bio = profile.get("bio", "")
            # Look for LinkedIn URL
            linkedin_patterns = [
                r'https?://(?:www\.)?linkedin\.com/in/[\w\-_]+/?',
                r'linkedin\.com/in/[\w\-_]+/?'
            ]
            for pattern in linkedin_patterns:
                import re
                linkedin_match = re.search(pattern, bio, re.IGNORECASE)
                if linkedin_match:
                    linkedin_url = linkedin_match.group(0)
                    if not linkedin_url.startswith('http'):
                        linkedin_url = 'https://' + linkedin_url
                    social_links['linkedin'] = linkedin_url
                    break

        context = {
            "profile": profile,
            "repos": repos_top,
            "all_repos": repos,
            "lang_labels": lang_labels,
            "lang_values": lang_values,
            "star_labels": star_labels,
            "star_values": star_values,
            "fork_labels": fork_labels,
            "fork_values": fork_values,
            "user_stats": user_stats,
            "social_links": social_links,
            "contribution_weeks": contribution_data.get("contribution_weeks", []),
            "total_contributions": contribution_data.get("total_contributions", 0)
        }

        return render(request, "public_card_simple.html", context)
        
    except requests.exceptions.RequestException as e:
        if "rate limit exceeded" in str(e).lower():
            return render(request, "error.html", {
                "error_title": "Rate Limit Exceeded",
                "error_message": "The GitHub API rate limit has been exceeded. Please try again later.",
                "error_icon": "fa-clock"
            })
        elif e.response and e.response.status_code == 404:
            return render(request, "error.html", {
                "error_title": "User Not Found",
                "error_message": f"Could not find GitHub user '{username}'. Please check the username and try again.",
                "error_icon": "fa-user-slash"
            })
        else:
            return render(request, "error.html", {
                "error_title": "GitHub API Error",
                "error_message": "An error occurred while fetching user data. Please try again.",
                "error_icon": "fa-exclamation-triangle"
            })


def compare_users(request):
    """Compare multiple GitHub users side by side"""
    usernames = request.GET.getlist('users[]')
    if len(usernames) < 2:
        return render(request, "compare.html", {"error": "Please select at least 2 users to compare"})
    
    client = GitHubClient(access_token=None)
    users_data = []
    
    for username in usernames[:4]:  # Limit to 4 users
        try:
            profile = client.get_public_user(username)
            repos = client.get_public_repos(username)
            user_stats = client.get_user_stats(username)
            
            users_data.append({
                "profile": profile,
                "stats": user_stats,
                "repo_count": len(repos)
            })
        except Exception:
            continue
    
    return render(request, "compare.html", {"users": users_data})


@login_required
@require_POST
def reorder_highlights(request):
    # Expect JSON: { order: [highlight_id, ...] }
    order = request.POST.getlist("order[]") or []
    for idx, highlight_id in enumerate(order):
        try:
            ph = PortfolioHighlight.objects.get(id=int(highlight_id), user=request.user)
            ph.order = idx
            ph.save(update_fields=["order"])
        except (ValueError, PortfolioHighlight.DoesNotExist):
            continue
    return JsonResponse({"ok": True})
