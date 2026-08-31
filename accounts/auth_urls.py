from django.urls import path

from .auth_views import LoginView, MeView, RefreshView

urlpatterns = [
    path("login/", LoginView.as_view(), name="auth_login"),
    path("refresh/", RefreshView.as_view(), name="auth_refresh"),
    path("me/", MeView.as_view(), name="auth_me"),
]
