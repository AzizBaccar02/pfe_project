from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .serializers_verify import VerifyEmailSerializer
from .serializers import UserPublicSerializer
from .tokens import CustomRefreshToken


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        refresh = CustomRefreshToken.for_user(user)
        access = refresh.access_token

        return Response(
            {
                "message": "Email verified successfully.",
                "user": UserPublicSerializer(user).data,
                "refresh": str(refresh),
                "access": str(access),
            },
            status=status.HTTP_200_OK,
        )