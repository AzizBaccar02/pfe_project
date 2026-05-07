from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import Role
from offers.models import Offre, OffreStatut
from interactions.models import OffreReaction, OfferReactionStatus
from subscriptions.services.usage_service import (
    consume_subscription_usage,
    SubscriptionUsageAction,
)
from chats.models import Chat, ChatStatus
from chats.serializers import ChatSerializer

from .serializers import OffreReactionSerializer


def parse_bool(value):
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        value = value.strip().lower()

        if value in ["true", "1", "yes", "y"]:
            return True

        if value in ["false", "0", "no", "n"]:
            return False

    return None


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

        react_value = parse_bool(request.data.get("react"))

        if react_value is None:
            return Response(
                {"detail": "react is required and must be true or false."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = OffreReactionSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        reaction_status = (
            OfferReactionStatus.PENDING
            if react_value is True
            else OfferReactionStatus.REJECTED
        )

        with transaction.atomic():
            consume_subscription_usage(
                request.user,
                SubscriptionUsageAction.LIKE_OFFER,
            )

            reaction = serializer.save(
                agent=request.user,
                offre=offer,
                react=react_value,
                status=reaction_status,
            )

        return Response(
            OffreReactionSerializer(reaction).data,
            status=status.HTTP_201_CREATED,
        )


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


class ClientRespondToOfferReactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, reaction_id):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can respond to interested agents."},
                status=status.HTTP_403_FORBIDDEN,
            )

        accept_value = parse_bool(request.data.get("accept"))

        if accept_value is None:
            return Response(
                {"detail": "accept is required and must be true or false."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            reaction = (
                OffreReaction.objects
                .select_related("offre", "agent", "offre__client")
                .get(id=reaction_id)
            )
        except OffreReaction.DoesNotExist:
            return Response(
                {"detail": "Reaction not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if reaction.offre.client_id != request.user.id:
            return Response(
                {"detail": "You can only respond to reactions on your own offers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if reaction.react is False:
            return Response(
                {"detail": "This agent already rejected the offer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if reaction.status != OfferReactionStatus.PENDING:
            return Response(
                {"detail": "This reaction has already been handled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            reaction.status = (
                OfferReactionStatus.ACCEPTED
                if accept_value is True
                else OfferReactionStatus.REJECTED
            )
            reaction.save(update_fields=["status"])

            chat = None

            if accept_value is True:
                chat, created = Chat.objects.get_or_create(
                    offreReaction=reaction,
                    defaults={
                        "client": request.user,
                        "agent": reaction.agent,
                        "status": ChatStatus.ACTIVE,
                    },
                )

                update_fields = []

                if chat.client_id != request.user.id:
                    chat.client = request.user
                    update_fields.append("client")

                if chat.agent_id != reaction.agent_id:
                    chat.agent = reaction.agent
                    update_fields.append("agent")

                if chat.status != ChatStatus.ACTIVE:
                    chat.status = ChatStatus.ACTIVE
                    update_fields.append("status")

                if update_fields:
                    chat.save(update_fields=update_fields)

        reaction_data = OffreReactionSerializer(reaction).data

        if accept_value is True and chat is not None:
            return Response(
                {
                    "message": "Reaction accepted and chat created successfully.",
                    "reaction": reaction_data,
                    "chat": ChatSerializer(chat).data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "message": "Reaction rejected successfully.",
                "reaction": reaction_data,
                "chat": None,
            },
            status=status.HTTP_200_OK,
        )