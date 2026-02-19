from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
import random
import string

from .models import PasswordResetCode

User = get_user_model()


def generate_code(length=6):
    return "".join(random.choices(string.digits, k=length))


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        email = value.strip().lower()
        try:
            self.user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Pro behavior: don't reveal if email exists
            self.user = None
        return email

    def save(self, **kwargs):
        if not self.user:
            return {"sent": True, "code": None, "user": None}  # pretend ok

        code = generate_code(6)
        PasswordResetCode.objects.create(
            user=self.user,
            code=code,
            expiresAt=timezone.now() + timedelta(minutes=15),
            isUsed=False,
        )
        return {"sent": True, "code": code, "user": self.user}


class ResetPasswordConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=20)
    new_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        code = attrs["code"].strip()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "Invalid code or email."})

        reset = (
            PasswordResetCode.objects.filter(user=user, isUsed=False)
            .order_by("-createdAt")
            .first()
        )
        if not reset:
            raise serializers.ValidationError({"detail": "Invalid code or email."})

        if timezone.now() > reset.expiresAt:
            raise serializers.ValidationError({"code": "Code expired. Request a new one."})

        if reset.code != code:
            raise serializers.ValidationError({"code": "Invalid code."})

        attrs["user"] = user
        attrs["reset_obj"] = reset
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        reset = self.validated_data["reset_obj"]
        new_password = self.validated_data["new_password"]

        user.set_password(new_password)
        user.save(update_fields=["password"])

        reset.isUsed = True
        reset.save(update_fields=["isUsed"])

        return user
