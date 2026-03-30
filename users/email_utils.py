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
    message = f""" 
    Hello,
    
    Your JobMatch verification code is: {code}
    
    This code expires in 24 hours.
    
    If you did not create this account, please ignore this email.
    JobMatch Team
    """
    send_email(to_email, subject, message)
def send_password_reset_code_email(to_email: str, code: str) -> None:
    subject = "Password reset"
    message = f"""
    Hello,

    Your JobMatch password reset code is: {code}

    If you did not request a password reset, please ignore this email.

    JobMatch Team
    """
    send_email(to_email, subject, message)