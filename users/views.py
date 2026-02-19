from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .serializers import SignUpSerializer, UserPublicSerializer
from .email_utils import send_verification_code_email


class SignUpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = serializer.save()
        user = result["user"]
        code = result["code"]

        send_verification_code_email(user.email, code)

        return Response(
            {
                "message": "Account created. Please verify your email.",
                "user": UserPublicSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )
