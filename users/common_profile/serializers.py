from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.models import Profile

User = get_user_model()

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = [
            "phone",
            "photo",
            "bio",
            "skills",
            "hourlyRate",
            "rating",
            "localisation",
        ]

class MeSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "role",
            "isEmailVerified",
            "createdAt",
            "profile",
        ]

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["phone", "photo", "bio", "skills", "hourlyRate", "localisation"]