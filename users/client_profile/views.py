from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import Profile, Role
from .serializers import ClientProfileSerializer


class ClientProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can access this profile."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response(
                {"detail": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ClientProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can create this profile."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            request.user.profile
            return Response(
                {"detail": "Profile already exists. Use PUT or PATCH to update it."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Profile.DoesNotExist:
            pass

        serializer = ClientProfileSerializer(
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can update this profile."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response(
                {"detail": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ClientProfileSerializer(
            profile,
            data=request.data,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can update this profile."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            profile = request.user.profile
        except Profile.DoesNotExist:
            return Response(
                {"detail": "Profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ClientProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)