from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import VerificationCode

User = get_user_model()


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=20)

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        code = attrs["code"].strip()

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User not found."})

        try:
            v = VerificationCode.objects.get(user=user)
        except VerificationCode.DoesNotExist:
            raise serializers.ValidationError({"code": "No verification code found for this user."})

        if v.isUsed:
            raise serializers.ValidationError({"code": "This code is already used."})

        if timezone.now() > v.expiresAt:
            raise serializers.ValidationError({"code": "Code expired. Please request a new one."})

        if v.code != code:
            raise serializers.ValidationError({"code": "Invalid code."})

        attrs["user"] = user
        attrs["verification_obj"] = v
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        v = self.validated_data["verification_obj"]

        user.isEmailVerified = True
        user.save(update_fields=["isEmailVerified"])

        v.isUsed = True
        v.save(update_fields=["isUsed"])

        return user
