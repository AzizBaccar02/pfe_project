#interactions\views.py
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
from notifications.views import send_notification

from .serializers import (
    ClientInterestedAgentSerializer,
    OffreReactionSerializer,
)


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

        # Notify the client that an agent liked their offer
        if react_value is True:
            agent_name = request.user.get_full_name() or request.user.username
            send_notification(
                title=f"{agent_name} liked your offer",
                body=f'{agent_name} is interested in "{offer.title}".',
                notification_type="AGENT_LIKED_OFFER",
                user_id=offer.client_id,
                data={
                    "action":         "agent_liked_offer",
                    "offer_id":       offer.id,
                    "offer_title":    offer.title,
                    "agent_id":       request.user.id,
                    "agent_name":     agent_name,
                    "agent_email":    request.user.email,
                    "interaction_id": reaction.id,
                },
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


class ClientInterestedAgentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can access interested agents."},
                status=status.HTTP_403_FORBIDDEN,
            )

        offer_id = request.query_params.get("offer_id")

        reactions = (
            OffreReaction.objects
            .filter(
                offre__client=request.user,
                react=True,
                status=OfferReactionStatus.PENDING,
            )
            .select_related(
                "agent",
                "agent__profile",
                "agent__profile__localisation",
                "offre",
            )
            .order_by("-createdAt")
        )

        if offer_id is not None and str(offer_id).strip():
            try:
                offer_id_value = int(offer_id)
            except ValueError:
                return Response(
                    {"detail": "offer_id must be a valid integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            reactions = reactions.filter(offre_id=offer_id_value)

        serializer = ClientInterestedAgentSerializer(
            reactions,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data, status=status.HTTP_200_OK)


class ClientOfferReactionsView(APIView):
    """List all offer reactions on the client's offers (any status)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can access offer reactions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        status_param = request.query_params.get("status")
        offer_id = request.query_params.get("offer_id")

        reactions = (
            OffreReaction.objects
            .filter(
                offre__client=request.user,
                react=True,
            )
            .select_related(
                "agent",
                "agent__profile",
                "agent__profile__localisation",
                "offre",
            )
            .order_by("-createdAt")
        )

        if status_param is not None and str(status_param).strip():
            reactions = reactions.filter(
                status=str(status_param).strip().upper(),
            )

        if offer_id is not None and str(offer_id).strip():
            try:
                reactions = reactions.filter(offre_id=int(offer_id))
            except ValueError:
                return Response(
                    {"detail": "offer_id must be a valid integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        serializer = ClientInterestedAgentSerializer(
            reactions,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class ClientOfferReactionLookupView(APIView):
    """Return a single offer reaction for the client (any status)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can access offer reactions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        reaction_id = request.query_params.get("reaction_id")
        offer_id = request.query_params.get("offer_id")
        agent_id = request.query_params.get("agent_id")

        reactions = (
            OffreReaction.objects
            .filter(
                offre__client=request.user,
                react=True,
            )
            .select_related(
                "agent",
                "agent__profile",
                "agent__profile__localisation",
                "offre",
            )
        )

        if reaction_id is not None and str(reaction_id).strip():
            try:
                reactions = reactions.filter(id=int(reaction_id))
            except ValueError:
                return Response(
                    {"detail": "reaction_id must be a valid integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif offer_id is not None and agent_id is not None:
            try:
                reactions = reactions.filter(
                    offre_id=int(offer_id),
                    agent_id=int(agent_id),
                )
            except ValueError:
                return Response(
                    {
                        "detail": "offer_id and agent_id must be valid integers.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {
                    "detail": "Provide reaction_id or both offer_id and agent_id.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        reaction = reactions.order_by("-createdAt").first()

        if not reaction:
            return Response(
                {"detail": "Offer reaction not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ClientInterestedAgentSerializer(
            reaction,
            context={"request": request},
        )
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

        # Notify the agent of the client's decision
        client_name = request.user.get_full_name() or request.user.username
        offer = reaction.offre

        if accept_value is True:
            send_notification(
                title="Your interest was accepted!",
                body=f'{client_name} accepted your interest in "{offer.title}".',
                notification_type="MATCH_CREATED",
                user_id=reaction.agent_id,
                data={
                    "action":         "client_accepted",
                    "offer_id":       offer.id,
                    "offer_title":    offer.title,
                    "client_id":      request.user.id,
                    "client_name":    client_name,
                    "interaction_id": reaction.id,
                    "chat_id":        chat.id if chat else None,
                },
            )
        else:
            send_notification(
                title="Your interest was declined",
                body=f'{client_name} declined your interest in "{offer.title}".',
                notification_type="CLIENT_REJECTED",
                user_id=reaction.agent_id,
                data={
                    "action":         "client_rejected",
                    "offer_id":       offer.id,
                    "offer_title":    offer.title,
                    "client_id":      request.user.id,
                    "client_name":    client_name,
                    "interaction_id": reaction.id,
                },
            )

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