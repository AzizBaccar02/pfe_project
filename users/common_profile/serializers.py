from rest_framework import serializers
from django.contrib.auth import get_user_model
from users.models import Profile, Role

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
    isProfileCompleted = serializers.SerializerMethodField()

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
            "isProfileCompleted",
        ]

    def get_isProfileCompleted(self, obj):
        profile = getattr(obj, "profile", None)
        if not profile:
            return False

        if obj.role == Role.CLIENT:
            return bool(
                profile.phone and
                profile.phone.strip() and
                profile.localisation is not None
            )

        if obj.role == Role.AGENT:
            return bool(
                profile.phone and
                profile.phone.strip() and
                profile.bio and
                profile.bio.strip() and
                profile.skills and
                profile.skills.strip() and
                profile.hourlyRate is not None and
                profile.hourlyRate > 0 and
                profile.localisation is not None
            )

        return False


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ["phone", "photo", "bio", "skills", "hourlyRate", "localisation"]