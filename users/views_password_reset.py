from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .serializers_password_reset import (
    ForgotPasswordSerializer,
    ResetPasswordConfirmSerializer,
)
from .email_utils import send_password_reset_code_email


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        # If user exists, send email (console prints it)
        if result["user"] is not None:
            send_password_reset_code_email(result["user"].email, result["code"])

        # Always return same message (security)
        return Response(
            {"message": "If the email exists, a reset code has been sent."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Password reset successful. You can login now."},
            status=status.HTTP_200_OK,
        )
