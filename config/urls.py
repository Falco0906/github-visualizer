from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("social_django.urls", namespace="social")),
    path("accounts/", include("accounts.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("github/", include("githubapi.urls")),
    path("portfolio/", include("portfolio.urls")),
    path("login-error/", TemplateView.as_view(template_name="login_error.html"), name="login_error"),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
]
