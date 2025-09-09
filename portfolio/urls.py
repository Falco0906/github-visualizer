from django.urls import path
from . import views

urlpatterns = [
    path("u/<str:username>/", views.public_portfolio, name="public_portfolio"),
    path("viewer/<str:username>/", views.public_viewer, name="public_viewer"),
    path("search/", views.search_redirect, name="search_redirect"),
    path("compare/", views.compare_users, name="compare_users"),
    path("reorder/", views.reorder_highlights, name="reorder_highlights"),
]
