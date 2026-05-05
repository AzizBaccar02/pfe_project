from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated


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
                "message": "Account created successfully. Verification code sent to email.",
                "user": UserPublicSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def _serialize_user(self, user):
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "isEmailVerified": user.isEmailVerified,
            "createdAt": user.createdAt,
        }

    def get(self, request):
        return Response(
            self._serialize_user(request.user),
            status=status.HTTP_200_OK,
        )

    def patch(self, request):
        user = request.user

        first_name = request.data.get("first_name", request.data.get("firstName"))
        last_name = request.data.get("last_name", request.data.get("lastName"))

        update_fields = []

        if first_name is not None:
            user.first_name = str(first_name).strip()
            update_fields.append("first_name")

        if last_name is not None:
            user.last_name = str(last_name).strip()
            update_fields.append("last_name")

        if update_fields:
            user.save(update_fields=update_fields)

        return Response(
            self._serialize_user(user),
            status=status.HTTP_200_OK,
        )

    def put(self, request):
        return self.patch(request)