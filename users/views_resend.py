from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from .serializers_resend import ResendCodeSerializer
from .email_utils import send_verification_code_email

class ResendCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        if result["already_verified"]:
            return Response(
                {"message": "Email already verified"},
                status=status.HTTP_200_OK,
            )

        # This prints the email in console
        send_verification_code_email(result["user"].email, result["code"])

        return Response(
            {
                "message": "Verification code resent.",
                },
            status=status.HTTP_200_OK,
        )