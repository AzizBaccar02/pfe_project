from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
from django.db import transaction
import random
import string

from .models import Profile, VerificationCode, Role

User = get_user_model()


def generate_code(length=6):
    return "".join(random.choices(string.digits, k=length))


class SignUpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    username = serializers.CharField(required=False, allow_blank=True, max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    role = serializers.ChoiceField(choices=Role.choices)

    phone = serializers.CharField(required=False, allow_blank=True, max_length=30)
    bio = serializers.CharField(required=False, allow_blank=True)
    skills = serializers.CharField(required=False, allow_blank=True)
    hourlyRate = serializers.FloatField(required=False)
    localisation_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_email(self, value):
        value = value.lower().strip()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_username(self, value):
        value = (value or "").strip()
        # if user provided username, it must be unique
        if value and User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value

    @transaction.atomic
    def create(self, validated_data):
        email = validated_data["email"]
        password = validated_data["password"]
        role = validated_data["role"]

        # base username: provided or email prefix
        base_username = (validated_data.get("username") or email.split("@")[0]).strip()
        if not base_username:
            base_username = "user"

        # ensure username unique (auto add number if taken)
        username = base_username
        i = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{i}"
            i += 1

        user = User(
            email=email,
            username=username,
            role=role,
            isEmailVerified=False,
        )
        user.set_password(password)
        user.save()

        Profile.objects.create(
            user=user,
            phone=validated_data.get("phone", ""),
            bio=validated_data.get("bio", ""),
            skills=validated_data.get("skills", ""),
            hourlyRate=validated_data.get("hourlyRate", 0.0),
            rating=0.0,
            localisation_id=validated_data.get("localisation_id", None),
            photo=None,
        )

        code = generate_code(6)
        VerificationCode.objects.update_or_create(
            user=user,
            defaults={
                "code": code,
                "expiresAt": timezone.now() + timedelta(hours=24),
                "isUsed": False,
            },
        )

        return {"user": user, "code": code}


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "role", "isEmailVerified", "createdAt"]
