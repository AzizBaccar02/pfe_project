from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework import status

from users.models import Profile, Role
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