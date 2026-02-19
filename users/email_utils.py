from django.conf import settings
from django.core.mail import send_mail


def send_email(to_email: str, subject: str, message: str) -> None:
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=False,
    )


def send_verification_code_email(to_email: str, code: str) -> None:
    subject = "Email verification"
    message = f"Your verification code is: {code}"
    send_email(to_email, subject, message)

def send_password_reset_code_email(to_email: str, code: str) -> None:
    subject = "Password reset"
    message = f"Your password reset code is: {code}"
    send_email(to_email, subject, message)