from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers

from .tokens import CustomRefreshToken  # ✅ add this import

User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        email = (attrs.get("email") or "").strip().lower()
        password = attrs.get("password")

        if not email or not password:
            raise serializers.ValidationError("Email and password are required.")

        try:
            u = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("No active account found with the given credentials")

        user = authenticate(username=u.username, password=password)
        if user is None or not user.is_active:
            raise serializers.ValidationError("No active account found with the given credentials")

        # ✅ use your custom token so it contains role
        refresh = CustomRefreshToken.for_user(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
