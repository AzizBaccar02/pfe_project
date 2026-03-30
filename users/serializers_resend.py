from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
import random
import string

from .models import VerificationCode

User = get_user_model()


def generate_code(length=6):
    return "".join(random.choices(string.digits, k=length))


class ResendCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        email = value.strip().lower()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")
        self.user = user
        return email

    def save(self, **kwargs):
        user = self.user

        # Optional: if already verified, don't resend
        if user.isEmailVerified:
            return {"user": user, "code": None, "already_verified": True}

        code = generate_code(6)
        VerificationCode.objects.update_or_create(
            user=user,
            defaults={
                "code": code,
                "expiresAt": timezone.now() + timedelta(hours=24),
                "isUsed": False,
            },
        )
        return {"user": user, "code": code, "already_verified": False}
