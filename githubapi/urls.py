from django.urls import path
from django.http import JsonResponse


def healthcheck(_):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", healthcheck, name="github_health"),
]
