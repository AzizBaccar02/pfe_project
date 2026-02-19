from django.urls import path
from .views import SignUpView
from .views_password_reset import ForgotPasswordView, ResetPasswordConfirmView
from .views_resend import ResendCodeView
from .views_verify import VerifyEmailView

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify_email"),
    path("resend-code/", ResendCodeView.as_view(), name="resend_code"),
    path("forgot-password/", ForgotPasswordView.as_view(), name="forgot_password"),
    path("reset-password/", ResetPasswordConfirmView.as_view(), name="reset_password"),
]
