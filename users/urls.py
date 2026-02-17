from django.urls import path
from .views import SignUpView
from .views_verify import VerifyEmailView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify_email"),
]
