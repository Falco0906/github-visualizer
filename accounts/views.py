from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages

from accounts.forms import UserProfileForm, UserPreferencesForm
from githubapi.services import GitHubIngestService
from portfolio.models import Repository, PortfolioHighlight


@login_required
def dashboard(request):
    # Ensure data cached
    GitHubIngestService(request.user).sync_all()

    repos = Repository.objects.filter(owner=request.user).order_by("-stargazers_count")[:12]
    highlights = PortfolioHighlight.objects.filter(user=request.user).order_by("order")

    # Chart data
    languages = {}
    for repo in Repository.objects.filter(owner=request.user):
        for language, bytes_used in (repo.languages or {}).items():
            languages[language] = languages.get(language, 0) + bytes_used

    context = {
        "repos": repos,
        "highlights": highlights,
        "lang_labels": list(languages.keys()),
        "lang_values": list(languages.values()),
    }
    return render(request, "dashboard.html", context)


@login_required
def edit_profile(request):
    from accounts.models import UserProfile, UserPreferences

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    prefs, _ = UserPreferences.objects.get_or_create(user=request.user)

    if request.method == "POST":
        pf = UserProfileForm(request.POST, instance=profile)
        pr = UserPreferencesForm(request.POST, instance=prefs)
        if pf.is_valid() and pr.is_valid():
            pf.save()
            pr.save()
            messages.success(request, "Profile updated!")
            return redirect(reverse("dashboard"))
    else:
        pf = UserProfileForm(instance=profile)
        pr = UserPreferencesForm(instance=prefs)

    return render(request, "profile_edit.html", {"profile_form": pf, "prefs_form": pr})


def connect_github(request):
    return redirect(reverse("social:begin", args=["github"]))
