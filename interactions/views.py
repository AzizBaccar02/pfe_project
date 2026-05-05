from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import Role
from offers.models import Offre, OffreStatut
from interactions.models import OffreReaction
from subscriptions.services.usage_service import (
    consume_subscription_usage,
    SubscriptionUsageAction,
)

from .serializers import OffreReactionSerializer


class AgentOfferReactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, offer_id):
        if request.user.role != Role.AGENT:
            return Response(
                {"detail": "Only agents can react to offers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            offer = Offre.objects.get(id=offer_id, status=OffreStatut.OPEN)
        except Offre.DoesNotExist:
            return Response(
                {"detail": "Offer not found or not open."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if offer.client_id == request.user.id:
            return Response(
                {"detail": "You cannot react to your own offer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if OffreReaction.objects.filter(agent=request.user, offre=offer).exists():
            return Response(
                {"detail": "You have already reacted to this offer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OffreReactionSerializer(data=request.data)

        if serializer.is_valid():
            react_value = serializer.validated_data.get("react", True)

            with transaction.atomic():
                if react_value is True:
                    consume_subscription_usage(
                        request.user,
                        SubscriptionUsageAction.LIKE_OFFER,
                    )

                reaction = serializer.save(
                    agent=request.user,
                    offre=offer,
                )

            return Response(
                OffreReactionSerializer(reaction).data,
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MyOfferReactionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != Role.AGENT:
            return Response(
                {"detail": "Only agents can access their reactions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        reactions = (
            OffreReaction.objects
            .filter(agent=request.user)
            .select_related("offre", "agent")
            .order_by("-createdAt")
        )

        serializer = OffreReactionSerializer(reactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)