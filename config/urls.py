from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from users.views_auth import LoginView
from users.views_logout import LogoutView
urlpatterns = [
    path("admin/", admin.site.urls),

    # users
    path("api/users/", include("users.urls")),

    # auth
    path("api/auth/login/", LoginView.as_view(), name="login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/logout/", LogoutView.as_view(), name="logout"),
]
