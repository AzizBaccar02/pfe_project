from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .serializers import SignUpSerializer, UserPublicSerializer
from .tokens import CustomRefreshToken


def get_tokens_for_user(user):
    refresh = CustomRefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class SignUpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = serializer.save()
        user = result["user"]

        tokens = get_tokens_for_user(user)

        return Response(
            {
                "message": "Account created. Logged in successfully.",
                "user": UserPublicSerializer(user).data,
                "tokens": tokens,
            },
            status=status.HTTP_201_CREATED,
        )
