##chats/views.py

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Chat, Message, ChatStatus
from .serializers import ChatSerializer, MessageSerializer


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
                {"error": "You can only create a chat where you are the client or the agent."},
                status=status.HTTP_403_FORBIDDEN,
            )

        chat = serializer.save()
        return Response(ChatSerializer(chat).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_chats(request):
    chats = Chat.objects.filter(
        Q(client=request.user) | Q(agent=request.user)
    ).distinct()

    serializer = ChatSerializer(chats, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_chat_by_id(request, chat_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.user.id not in [chat.client_id, chat.agent_id]:
        return Response(
            {"error": "You are not allowed to access this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = ChatSerializer(chat)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_chat(request, chat_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)

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
        return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.user.id not in [chat.client_id, chat.agent_id]:
        return Response(
            {"error": "You are not allowed to delete this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    chat.delete()
    return Response({"message": "Chat deleted successfully"}, status=status.HTTP_200_OK)


# ---------------------------
# MESSAGE CRUD
# ---------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_message(request, chat_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)

    if chat.status != ChatStatus.ACTIVE:
        return Response({"error": "Chat is closed"}, status=status.HTTP_400_BAD_REQUEST)

    if request.user.id not in [chat.client_id, chat.agent_id]:
        return Response(
            {"error": "You are not allowed to send messages in this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = MessageSerializer(data=request.data)

    if serializer.is_valid():
        message = serializer.save(chat=chat, sender=request.user, isRead=False)
        data = MessageSerializer(message).data

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{chat.id}",
            {
                "type": "chat_message",
                "message": data,
            }
        )

        return Response(data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_messages_by_chat_id(request, chat_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.user.id not in [chat.client_id, chat.agent_id]:
        return Response(
            {"error": "You are not allowed to access messages of this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    messages = Message.objects.filter(chat_id=chat_id).order_by("sentAt")
    serializer = MessageSerializer(messages, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_message(request, chat_id, message_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        message = Message.objects.get(id=message_id, chat=chat)
    except Message.DoesNotExist:
        return Response({"error": "Message not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.user != message.sender:
        return Response(
            {"error": "You can only update your own messages"},
            status=status.HTTP_403_FORBIDDEN,
        )

    partial = request.method == "PATCH"
    serializer = MessageSerializer(message, data=request.data, partial=partial)

    if serializer.is_valid():
        updated_message = serializer.save(chat=chat, sender=message.sender)
        return Response(MessageSerializer(updated_message).data, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_message(request, chat_id, message_id):
    try:
        chat = Chat.objects.get(id=chat_id)
    except Chat.DoesNotExist:
        return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        message = Message.objects.get(id=message_id, chat=chat)
    except Message.DoesNotExist:
        return Response({"error": "Message not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.user != message.sender:
        return Response(
            {"error": "You can only delete your own messages"},
            status=status.HTTP_403_FORBIDDEN,
        )

    message.delete()
    return Response({"message": "Message deleted successfully"}, status=status.HTTP_200_OK)


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
            status=status.HTTP_404_NOT_FOUND
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
        isRead=False
    ).update(isRead=True)

    unread_count = Message.objects.filter(
        chat=chat,
        sender_id=other_user_id,
        isRead=False
    ).count()

    # real-time seen event
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"chat_{chat.id}",
        {
            "type": "messages_seen",
            "reader_id": request.user.id,
        }
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
        return Response({"error": "Chat not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.user.id not in [chat.client_id, chat.agent_id]:
        return Response(
            {"error": "You are not allowed to close this chat"},
            status=status.HTTP_403_FORBIDDEN,
        )

    chat.status = ChatStatus.CLOSED
    chat.save()

    return Response(
        {"message": "Chat closed successfully", "status": chat.status},
        status=status.HTTP_200_OK,
    )