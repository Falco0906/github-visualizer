from django import forms
from .models import UserProfile, UserPreferences


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            "github_username",
            "bio",
            "company",
            "location",
            "blog",
        ]


class UserPreferencesForm(forms.ModelForm):
    class Meta:
        model = UserPreferences
        fields = [
            "theme",
            "primary_color",
            "accent_color",
            "bio_intro",
        ]
        widgets = {
            "primary_color": forms.TextInput(attrs={"type": "color"}),
            "accent_color": forms.TextInput(attrs={"type": "color"}),
        }
