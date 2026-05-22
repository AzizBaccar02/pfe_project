from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status

from users.models import Profile, Role, CustomUser
from .serializers import AgentProfileSerializer


class AgentProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = AgentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user.profile

    def get(self, request, *args, **kwargs):
        if request.user.role != Role.AGENT:
            return Response(
                {"detail": "Only agents can access this profile."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        if request.user.role != Role.AGENT:
            return Response(
                {"detail": "Only agents can update this profile."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        if request.user.role != Role.AGENT:
            return Response(
                {"detail": "Only agents can update this profile."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return self.partial_update(request, *args, **kwargs)


class AgentPublicProfileView(generics.RetrieveAPIView):
    serializer_class = AgentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id, *args, **kwargs):
        try:
            user = CustomUser.objects.get(id=user_id, role=Role.AGENT)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "Agent not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return Response(
                {"detail": "Agent profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = AgentProfileSerializer(profile).data
        data["first_name"] = user.first_name
        data["last_name"] = user.last_name
        data["email"] = user.email

        return Response(data, status=status.HTTP_200_OK)