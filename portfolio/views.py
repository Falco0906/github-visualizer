from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.http import require_POST

from .models import PortfolioHighlight
from githubapi.services import GitHubClient


def public_portfolio(request, username: str):
    highlights = PortfolioHighlight.objects.filter(user__username=username).select_related("repo")
    return render(request, "public_portfolio.html", {"username": username, "highlights": highlights})


def search_redirect(request):
    q = request.GET.get("q", "").strip()
    if not q:
        return redirect("home")
    # GitHub usernames are case-insensitive, use as-is for the API call
    return redirect("public_viewer", username=q)


def public_viewer(request, username: str):
    client = GitHubClient(access_token=None)
    try:
        profile = client.get_public_user(username)
    except Exception as e:
        if "rate limit exceeded" in str(e).lower():
            return render(request, "rate_limit.html", {"username": username})
        raise Http404("User not found")
    
    # fetch all repos
    repos = client.get_public_repos(username)
    # top repos by stars
    repos_top = sorted(repos, key=lambda r: (r.get("stargazers_count", 0), r.get("forks_count", 0)), reverse=True)[:8]

    # languages aggregation across all repos
    languages = {}
    for repo in repos:
        lang = repo.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1

    # Get additional stats
    user_stats = client.get_user_stats(username)
    contributions = client.get_contributions(username)

    # stars chart data for top repos
    star_labels = [r.get("name") for r in repos_top]
    star_values = [r.get("stargazers_count", 0) for r in repos_top]

    # forks chart data
    fork_labels = [r.get("name") for r in repos_top]
    fork_values = [r.get("forks_count", 0) for r in repos_top]

    # Language distribution for pie chart
    lang_data = sorted(languages.items(), key=lambda x: x[1], reverse=True)[:10]
    lang_labels = [item[0] for item in lang_data]
    lang_values = [item[1] for item in lang_data]

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
        "contributions": contributions,
    }
    return render(request, "public_card_simple.html", context)


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
