##views

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from users.models import Role

from .models import Chat, Message, ChatStatus
from .serializers import ChatSerializer, MessageSerializer
from .services.message_moderation_service import (
    build_moderation_response_data,
    moderate_message_content,
)


# ---------------------------
# HELPERS
# ---------------------------

def _user_data(user):
    if not user:
        return None

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "role": user.role,
    }


def _offer_data(offer):
    if not offer:
        return None

    localisation = getattr(offer, "localisation", None)
    category = getattr(offer, "category", None)

    return {
        "id": offer.id,
        "title": offer.title,
        "description": offer.description,
        "budget": offer.budget,
        "status": offer.status,
        "category": category.name if category else "",
        "city": localisation.city if localisation else "",
        "address": localisation.address if localisation else "",
        "postalCode": localisation.postalCode if localisation else "",
    }


def _reaction_data(reaction):
    if not reaction:
        return None

    return {
        "id": reaction.id,
        "status": reaction.status,
        "react": reaction.react,
        "message": reaction.message,
        "proposedPrice": reaction.proposedPrice,
        "createdAt": reaction.createdAt,
        "agentId": reaction.agent_id,
        "offreId": reaction.offre_id,
    }


def _last_message_data(message):
    if not message:
        return None

    return {
        "id": message.id,
        "content": message.content,
        "senderId": message.sender_id,
        "isRead": message.isRead,
        "sentAt": message.sentAt,
    }


def _chat_data(chat, current_user):
    if current_user.role == Role.CLIENT:
        other_user = chat.agent
    else:
        other_user = chat.client

    offre_reaction = getattr(chat, "offreReaction", None)
    offer = offre_reaction.offre if offre_reaction else None

    last_message = (
        Message.objects
        .filter(chat=chat)
        .order_by("-sentAt")
        .first()
    )

    unread_count = (
        Message.objects
        .filter(
            chat=chat,
            isRead=False,
        )
        .exclude(sender=current_user)
        .count()
    )

    return {
        "id": chat.id,
        "status": chat.status,
        "client": _user_data(chat.client),
        "agent": _user_data(chat.agent),
        "otherUser": _user_data(other_user),
        "offreReaction": _reaction_data(offre_reaction),
        "offer": _offer_data(offer),
        "lastMessage": _last_message_data(last_message),
        "unreadCount": unread_count,
    }


# ---------------------------
# CHAT CRUD
# ---------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_chat(request):
    serializer = ChatSerializer(data=request.data)

    if serializer.is_valid():
        client = serializer.validated_data["client"]
        agent = serializer.validated_data["agent"]

        if request.user.id not in [client.id, agent.id]:
            return Response(
                {
                    "error": "You can only create a chat where you are the client or the agent."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        chat = serializer.save()
        return Response(ChatSerializer(chat).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_chats(request):
    if request.user.role == Role.CLIENT:
        chats = Chat.objects.filter(client=request.user)

    elif request.user.role == Role.AGENT:
        chats = Chat.objects.filter(agent=request.user)

    else:
        return Response(
            {"error": "Only clients and agents can access chats."},
            status=status.HTTP_403_FORBIDDEN,
        )

    chats = (
        chats
        .select_related(
            "client",
            "agent",
            "offreReaction",
            "offreReaction__offre",
            "offreReaction__offre__category",
            "offreReaction__offre__localisation",
        )
        .order_by("-id")
    )

    data = [_chat_data(chat, request.user) for chat in chats]

    return Response(
        {
            "currentUserRole": request.user.role,
            "count": len(data),
            "chats": data,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_chat_by_id(request, chat_id):
    try:
        chat = (
            Chat.objects
            .select_related(
                "client",
                "agent",
                "offreReaction",
                "offreReaction__offre",
                "offreReaction__offre__category",
                "offreReaction__offre__localisation",
            )
            .get(id=chat_id)
        )
    except Chat.DoesNotExist:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.user.id not in [chat.client_id, chat.agent_id]:
        return Response(
            {"error": "You are not allowed to access this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    return Response(
        _chat_data(chat, request.user),
        status=status.HTTP_200_OK,
    )


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_chat(request, chat_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.user.id not in [chat.client_id, chat.agent_id]:
        return Response(
            {"error": "You are not allowed to update this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    partial = request.method == "PATCH"
    serializer = ChatSerializer(chat, data=request.data, partial=partial)

    if serializer.is_valid():
        updated_chat = serializer.save()
        return Response(ChatSerializer(updated_chat).data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_chat(request, chat_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.user.id not in [chat.client_id, chat.agent_id]:
        return Response(
            {"error": "You are not allowed to delete this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    chat.delete()
    return Response(
        {"message": "Chat deleted successfully"},
        status=status.HTTP_200_OK,
    )


# ---------------------------
# MESSAGE CRUD
# ---------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_message(request, chat_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if chat.status != ChatStatus.ACTIVE:
        return Response(
            {"error": "Chat is closed"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if request.user.id not in [chat.client_id, chat.agent_id]:
        return Response(
            {"error": "You are not allowed to send messages in this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    request_data = request.data.copy()
    original_content = request_data.get("content", "")

    moderated_content, has_warning, detected_words = moderate_message_content(
        original_content
    )

    request_data["content"] = moderated_content

    serializer = MessageSerializer(data=request_data)

    if serializer.is_valid():
        message = serializer.save(chat=chat, sender=request.user, isRead=False)
        data = MessageSerializer(message).data

        data = build_moderation_response_data(
            data=data,
            has_warning=has_warning,
            detected_words=detected_words,
        )

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{chat.id}",
            {
                "type": "chat_message",
                "message": data,
            },
        )

        return Response(data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_messages_by_chat_id(request, chat_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.user.id not in [chat.client_id, chat.agent_id]:
        return Response(
            {"error": "You are not allowed to access messages of this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    limit_param = request.query_params.get("limit")
    before_param = request.query_params.get("before")

    if not limit_param:
        messages = Message.objects.filter(chat_id=chat_id).order_by("sentAt", "id")
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    try:
        limit = int(limit_param)
    except (TypeError, ValueError):
        limit = 10

    limit = max(1, min(limit, 30))

    queryset = Message.objects.filter(chat_id=chat_id).order_by("-sentAt", "-id")

    if before_param:
        try:
            before_message = Message.objects.get(
                id=int(before_param),
                chat_id=chat_id,
            )
        except (ValueError, Message.DoesNotExist):
            return Response(
                {"error": "Invalid before cursor"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = queryset.filter(
            Q(sentAt__lt=before_message.sentAt)
            | Q(sentAt=before_message.sentAt, id__lt=before_message.id)
        )

    page_items = list(queryset[: limit + 1])

    has_more = len(page_items) > limit
    page_items = page_items[:limit]

    page_items.reverse()

    serializer = MessageSerializer(page_items, many=True)

    next_before = page_items[0].id if page_items else None

    return Response(
        {
            "results": serializer.data,
            "hasMore": has_more,
            "nextBefore": next_before,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_message(request, chat_id, message_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if chat.status != ChatStatus.ACTIVE:
        return Response(
            {"error": "Chat is closed"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        message = Message.objects.get(id=message_id, chat=chat)
    except Message.DoesNotExist:
        return Response(
            {"error": "Message not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.user != message.sender:
        return Response(
            {"error": "You can only update your own messages"},
            status=status.HTTP_403_FORBIDDEN,
        )

    request_data = request.data.copy()
    original_content = request_data.get("content", "").strip()

    if not original_content:
        return Response(
            {"error": "Message content cannot be empty"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    moderated_content, has_warning, detected_words = moderate_message_content(
        original_content
    )

    request_data["content"] = moderated_content

    serializer = MessageSerializer(message, data=request_data, partial=True)

    if serializer.is_valid():
        updated_message = serializer.save(chat=chat, sender=message.sender)
        data = MessageSerializer(updated_message).data

        data = build_moderation_response_data(
            data=data,
            has_warning=has_warning,
            detected_words=detected_words,
        )

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{chat.id}",
            {
                "type": "chat_message_updated",
                "message": data,
            },
        )

        return Response(data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_message(request, chat_id, message_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if chat.status != ChatStatus.ACTIVE:
        return Response(
            {"error": "Chat is closed"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        message = Message.objects.get(id=message_id, chat=chat)
    except Message.DoesNotExist:
        return Response(
            {"error": "Message not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.user != message.sender:
        return Response(
            {"error": "You can only delete your own messages"},
            status=status.HTTP_403_FORBIDDEN,
        )

    deleted_message_data = {
        "id": message.id,
        "chat": chat.id,
        "sender": message.sender_id,
    }

    message.delete()

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{chat.id}",
        {
            "type": "chat_message_deleted",
            "message": deleted_message_data,
        },
    )

    return Response(
        {
            "message": "Message deleted successfully",
            "deletedMessageId": deleted_message_data["id"],
            "chat": chat.id,
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------
# READ / STATUS APIs
# ---------------------------

@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def mark_all_messages_as_read(request, chat_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.user.id not in [chat.client_id, chat.agent_id]:
        return Response(
            {"error": "You are not allowed to access this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    if request.user.id == chat.client_id:
        other_user_id = chat.agent_id
    else:
        other_user_id = chat.client_id

    updated_count = Message.objects.filter(
        chat=chat,
        sender_id=other_user_id,
        isRead=False,
    ).update(isRead=True)

    unread_count = Message.objects.filter(
        chat=chat,
        sender_id=other_user_id,
        isRead=False,
    ).count()

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{chat.id}",
        {
            "type": "messages_seen",
            "reader_id": request.user.id,
        },
    )

    return Response(
        {
            "message": "All messages from the other participant marked as read",
            "chat_id": chat.id,
            "current_user": request.user.id,
            "other_user": other_user_id,
            "updated_count": updated_count,
            "unread_count": unread_count,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def close_chat(request, chat_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.user.id not in [chat.client_id, chat.agent_id]:
        return Response(
            {"error": "You are not allowed to close this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    chat.status = ChatStatus.CLOSED
    chat.save(update_fields=["status"])

    return Response(
        {"message": "Chat closed successfully", "status": chat.status},
        status=status.HTTP_200_OK,
    )