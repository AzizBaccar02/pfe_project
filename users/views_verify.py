from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .serializers_verify import VerifyEmailSerializer
from .serializers import UserPublicSerializer


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        return Response(
            {
                "message": "Email verified successfully.",
                "user": UserPublicSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )
