# chats/views.py

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from users.models import Role

from chats.presence import is_user_online
from .models import Chat, ChatStatus, Message
from .serializers import ChatSerializer, MessageSerializer
from .services.message_moderation_service import (
    build_moderation_response_data,
    moderate_message_content,
)


# ---------------------------
# HELPERS
# ---------------------------

def _parse_bool(value):
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()

    if normalized in ["true", "1", "yes", "y"]:
        return True

    if normalized in ["false", "0", "no", "n"]:
        return False

    return None


def _absolute_media_url(request, value):
    if not value:
        return ""

    clean_value = str(value).strip()

    if not clean_value or clean_value.lower() == "none":
        return ""

    if clean_value.startswith("http://") or clean_value.startswith("https://"):
        return clean_value

    if clean_value.startswith("//"):
        return f"http:{clean_value}"

    if not clean_value.startswith("/"):
        media_url = getattr(settings, "MEDIA_URL", "/media/")
        clean_value = f"{media_url.rstrip('/')}/{clean_value.lstrip('/')}"

    if request is not None:
        return request.build_absolute_uri(clean_value)

    return clean_value


def _safe_get_attr(obj, attr_name):
    try:
        return getattr(obj, attr_name, None)
    except ObjectDoesNotExist:
        return None
    except Exception:
        return None


def _photo_url_from_object(request, obj):
    if not obj:
        return ""

    possible_photo_fields = [
        "photo",
        "photoUrl",
        "photoURL",
        "photo_url",
        "profilePhoto",
        "profile_photo",
        "profileImage",
        "profile_image",
        "avatar",
        "avatarUrl",
        "avatar_url",
        "image",
        "imageUrl",
        "image_url",
    ]

    for field_name in possible_photo_fields:
        value = _safe_get_attr(obj, field_name)

        if not value:
            continue

        url = getattr(value, "url", None)

        if url:
            return _absolute_media_url(request, url)

        if isinstance(value, str) and value.strip():
            return _absolute_media_url(request, value)

    return ""


def _user_photo_url(request, user):
    if not user:
        return ""

    direct_photo_url = _photo_url_from_object(request, user)

    if direct_photo_url:
        return direct_photo_url

    possible_profile_relations = [
        "profile",
        "user_profile",
        "userProfile",
        "client_profile",
        "clientProfile",
        "clientprofile",
        "agent_profile",
        "agentProfile",
        "agentprofile",
    ]

    for relation_name in possible_profile_relations:
        profile = _safe_get_attr(user, relation_name)

        if not profile:
            continue

        profile_photo_url = _photo_url_from_object(request, profile)

        if profile_photo_url:
            return profile_photo_url

    return ""


def _broadcast_chat_list_update(chat, action):
    channel_layer = get_channel_layer()

    for user_id in [chat.client_id, chat.agent_id]:
        async_to_sync(channel_layer.group_send)(
            f"user_chats_{user_id}",
            {
                "type": "chat_list_updated",
                "chat_id": chat.id,
                "action": action,
            },
        )


def _user_data(user, request=None):
    if not user:
        return None

    photo_url = _user_photo_url(request, user)

    profile = _safe_get_attr(user, "profile")

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "role": user.role,
        "isOnline": is_user_online(user.id),

        # ✅ ADD THIS
        "phone": getattr(profile, "phone", None),

        "photo": photo_url,
        "photoUrl": photo_url,
        "profile": {
            "photo": photo_url,
        },
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


def _chat_state_for_user(chat, current_user):
    if current_user.id == chat.client_id:
        return {
            "customTitle": chat.clientCustomTitle,
            "isArchived": chat.clientArchived,
            "isMuted": chat.clientMuted,
        }

    return {
        "customTitle": chat.agentCustomTitle,
        "isArchived": chat.agentArchived,
        "isMuted": chat.agentMuted,
    }


def _chat_data(chat, current_user, request=None):
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

    state = _chat_state_for_user(chat, current_user)

    return {
        "id": chat.id,
        "status": chat.status,
        "client": _user_data(chat.client, request),
        "agent": _user_data(chat.agent, request),
        "otherUser": _user_data(other_user, request),
        "offreReaction": _reaction_data(offre_reaction),
        "offer": _offer_data(offer),
        "lastMessage": _last_message_data(last_message),
        "unreadCount": unread_count,
        "customTitle": state["customTitle"],
        "isArchived": state["isArchived"],
        "isMuted": state["isMuted"],
        "isBlocked": chat.blockedBy_id is not None,
        "blockedBy": chat.blockedBy_id,
        "blockedAt": chat.blockedAt,
    }


def _get_chat_or_404(chat_id):
    try:
        return (
            Chat.objects
            .select_related(
                "client",
                "agent",
                "offreReaction",
                "offreReaction__offre",
                "offreReaction__offre__category",
                "offreReaction__offre__localisation",
                "blockedBy",
            )
            .get(id=chat_id)
        )
    except Chat.DoesNotExist:
        return None


def _can_access_chat(user, chat):
    return user.id in [chat.client_id, chat.agent_id]


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
        _broadcast_chat_list_update(chat, "chat_created")

        return Response(
            _chat_data(chat, request.user, request),
            status=status.HTTP_201_CREATED,
        )

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
            "blockedBy",
        )
        .order_by("-id")
    )

    data = [_chat_data(chat, request.user, request) for chat in chats]

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
    chat = _get_chat_or_404(chat_id)

    if chat is None:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not _can_access_chat(request.user, chat):
        return Response(
            {"error": "You are not allowed to access this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    return Response(
        _chat_data(chat, request.user, request),
        status=status.HTTP_200_OK,
    )


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_chat(request, chat_id):
    chat = _get_chat_or_404(chat_id)

    if chat is None:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not _can_access_chat(request.user, chat):
        return Response(
            {"error": "You are not allowed to update this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    partial = request.method == "PATCH"
    serializer = ChatSerializer(chat, data=request.data, partial=partial)

    if serializer.is_valid():
        updated_chat = serializer.save()
        _broadcast_chat_list_update(updated_chat, "chat_updated")

        return Response(
            _chat_data(updated_chat, request.user, request),
            status=status.HTTP_200_OK,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_chat_preferences(request, chat_id):
    chat = _get_chat_or_404(chat_id)

    if chat is None:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not _can_access_chat(request.user, chat):
        return Response(
            {"error": "You are not allowed to update this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    custom_title = request.data.get("customTitle", None)
    is_archived = _parse_bool(request.data.get("isArchived", None))
    is_muted = _parse_bool(request.data.get("isMuted", None))

    update_fields = []

    if request.user.id == chat.client_id:
        if custom_title is not None:
            chat.clientCustomTitle = str(custom_title).strip()[:120]
            update_fields.append("clientCustomTitle")

        if is_archived is not None:
            chat.clientArchived = is_archived
            update_fields.append("clientArchived")

        if is_muted is not None:
            chat.clientMuted = is_muted
            update_fields.append("clientMuted")

    else:
        if custom_title is not None:
            chat.agentCustomTitle = str(custom_title).strip()[:120]
            update_fields.append("agentCustomTitle")

        if is_archived is not None:
            chat.agentArchived = is_archived
            update_fields.append("agentArchived")

        if is_muted is not None:
            chat.agentMuted = is_muted
            update_fields.append("agentMuted")

    if update_fields:
        chat.save(update_fields=update_fields)

    _broadcast_chat_list_update(chat, "chat_preferences_updated")

    return Response(
        _chat_data(chat, request.user, request),
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def block_chat(request, chat_id):
    chat = _get_chat_or_404(chat_id)

    if chat is None:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not _can_access_chat(request.user, chat):
        return Response(
            {"error": "You are not allowed to block this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    chat.status = ChatStatus.CLOSED
    chat.blockedBy = request.user
    chat.blockedAt = timezone.now()
    chat.save(update_fields=["status", "blockedBy", "blockedAt"])

    _broadcast_chat_list_update(chat, "chat_blocked")

    return Response(
        _chat_data(chat, request.user, request),
        status=status.HTTP_200_OK,
    )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_chat(request, chat_id):
    chat = _get_chat_or_404(chat_id)

    if chat is None:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not _can_access_chat(request.user, chat):
        return Response(
            {"error": "You are not allowed to delete this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    participant_ids = [chat.client_id, chat.agent_id]
    deleted_chat_id = chat.id
    chat.delete()

    channel_layer = get_channel_layer()

    for user_id in participant_ids:
        async_to_sync(channel_layer.group_send)(
            f"user_chats_{user_id}",
            {
                "type": "chat_list_updated",
                "chat_id": deleted_chat_id,
                "action": "chat_deleted",
            },
        )

    return Response(
        {
            "message": "Chat deleted successfully",
            "deletedChatId": deleted_chat_id,
        },
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

        _broadcast_chat_list_update(chat, "message_created")

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

        _broadcast_chat_list_update(chat, "message_updated")

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

    _broadcast_chat_list_update(chat, "message_deleted")

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

    _broadcast_chat_list_update(chat, "messages_seen")

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
    chat = _get_chat_or_404(chat_id)

    if chat is None:
        return Response(
            {"error": "Chat not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not _can_access_chat(request.user, chat):
        return Response(
            {"error": "You are not allowed to close this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    chat.status = ChatStatus.CLOSED
    chat.save(update_fields=["status"])

    _broadcast_chat_list_update(chat, "chat_closed")

    return Response(
        {"message": "Chat closed successfully", "status": chat.status},
        status=status.HTTP_200_OK,
    )