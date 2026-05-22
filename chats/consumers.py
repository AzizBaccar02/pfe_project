# chats/consumers.py

import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken

from chats.models import Chat, ChatStatus, Message
from chats.presence import mark_user_connected, mark_user_disconnected
from chats.services.message_moderation_service import (
    build_moderation_response_data,
    moderate_message_content,
)

User = get_user_model()


class JwtWebsocketAuthMixin:
    async def get_user_from_jwt(self):
        try:
            query_string = self.scope["query_string"].decode()
            query_params = parse_qs(query_string)
            token = query_params.get("token", [None])[0]

            if not token:
                return None

            validated_token = UntypedToken(token)
            return await self.get_user(validated_token)
        except (InvalidToken, TokenError, Exception):
            return None

    @database_sync_to_async
    def get_user(self, validated_token):
        token_backend = TokenBackend(
            algorithm="HS256",
            signing_key=settings.SECRET_KEY,
        )

        decoded_data = token_backend.decode(validated_token.token, verify=True)
        user_id = decoded_data.get("user_id")

        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None


class PresenceBroadcastMixin:
    @database_sync_to_async
    def get_presence_targets(self, user_id):
        chats = (
            Chat.objects
            .filter(
                Q(client_id=user_id) | Q(agent_id=user_id),
                status=ChatStatus.ACTIVE,
            )
            .values_list("id", "client_id", "agent_id")
        )

        chat_ids = []
        user_ids = {int(user_id)}

        for chat_id, client_id, agent_id in chats:
            chat_ids.append(chat_id)
            user_ids.add(client_id)
            user_ids.add(agent_id)

        return {
            "chat_ids": chat_ids,
            "user_ids": list(user_ids),
        }

    async def broadcast_presence_update(self, user_id, is_online):
        targets = await self.get_presence_targets(user_id)

        for target_user_id in targets["user_ids"]:
            await self.channel_layer.group_send(
                f"user_chats_{target_user_id}",
                {
                    "type": "presence_update",
                    "user_id": int(user_id),
                    "is_online": bool(is_online),
                },
            )

        for chat_id in targets["chat_ids"]:
            await self.channel_layer.group_send(
                f"chat_{chat_id}",
                {
                    "type": "presence_update",
                    "user_id": int(user_id),
                    "is_online": bool(is_online),
                },
            )


class UserChatsConsumer(
    JwtWebsocketAuthMixin,
    PresenceBroadcastMixin,
    AsyncWebsocketConsumer,
):
    async def connect(self):
        self.user = await self.get_user_from_jwt()

        if not self.user:
            await self.close()
            return

        self.group_name = f"user_chats_{self.user.id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        became_online = mark_user_connected(self.user.id)

        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection_established",
                    "message": f"Connected to {self.group_name}",
                }
            )
        )

        if became_online:
            await self.broadcast_presence_update(self.user.id, True)

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

        if hasattr(self, "user") and self.user:
            became_offline = mark_user_disconnected(self.user.id)

            if became_offline:
                await self.broadcast_presence_update(self.user.id, False)

    async def chat_list_updated(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat_list_updated",
                    "chat_id": event.get("chat_id"),
                    "action": event.get("action", "updated"),
                }
            )
        )

    async def presence_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "presence_update",
                    "user_id": event.get("user_id"),
                    "is_online": event.get("is_online", False),
                }
            )
        )


class ChatConsumer(
    JwtWebsocketAuthMixin,
    PresenceBroadcastMixin,
    AsyncWebsocketConsumer,
):
    async def connect(self):
        self.chat_id = self.scope["url_route"]["kwargs"]["chat_id"]
        self.group_name = f"chat_{self.chat_id}"

        self.user = await self.get_user_from_jwt()

        if not self.user:
            await self.close()
            return

        allowed = await self.user_can_access_chat(self.user.id, self.chat_id)

        if not allowed:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        became_online = mark_user_connected(self.user.id)

        if became_online:
            await self.broadcast_presence_update(self.user.id, True)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

        if hasattr(self, "user") and self.user:
            became_offline = mark_user_disconnected(self.user.id)

            if became_offline:
                await self.broadcast_presence_update(self.user.id, False)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(
                text_data=json.dumps(
                    {
                        "error": "Invalid JSON format.",
                    }
                )
            )
            return

        content = data.get("content", "").strip()

        if not content:
            await self.send(
                text_data=json.dumps(
                    {
                        "error": "content is required",
                    }
                )
            )
            return

        allowed = await self.user_can_access_chat(self.user.id, self.chat_id)

        if not allowed:
            await self.send(
                text_data=json.dumps(
                    {
                        "error": "You are not allowed to send messages in this chat",
                    }
                )
            )
            return

        moderated_content, has_warning, detected_words = moderate_message_content(
            content
        )

        message_data = await self.create_message(
            chat_id=self.chat_id,
            sender_id=self.user.id,
            content=moderated_content,
        )

        message_data = build_moderation_response_data(
            data=message_data,
            has_warning=has_warning,
            detected_words=detected_words,
        )

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat_message",
                "message": message_data,
            },
        )

        await self.broadcast_chat_list_update(
            chat_id=self.chat_id,
            action="message_created",
        )

    async def chat_message(self, event):
        message = event["message"]

        await self.send(
            text_data=json.dumps(
                {
                    "type": "new_message",
                    "message": message,
                }
            )
        )

        if message["sender"] != self.user.id:
            updated = await self.mark_message_as_read(message["id"], self.user.id)

            if updated:
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "message_seen",
                        "message_id": message["id"],
                        "reader_id": self.user.id,
                    },
                )

                await self.broadcast_chat_list_update(
                    chat_id=self.chat_id,
                    action="messages_seen",
                )

    async def chat_message_updated(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_updated",
                    "message": event["message"],
                }
            )
        )

    async def chat_message_deleted(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_deleted",
                    "message": event["message"],
                    "message_id": event["message"]["id"],
                }
            )
        )

    async def message_seen(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message_seen",
                    "message_id": event["message_id"],
                    "reader_id": event["reader_id"],
                }
            )
        )

    async def messages_seen(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "messages_seen",
                    "reader_id": event["reader_id"],
                }
            )
        )

    async def presence_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "presence_update",
                    "user_id": event.get("user_id"),
                    "is_online": event.get("is_online", False),
                }
            )
        )

    @database_sync_to_async
    def user_can_access_chat(self, user_id, chat_id):
        try:
            chat = Chat.objects.get(id=chat_id)
        except Chat.DoesNotExist:
            return False

        if chat.status != ChatStatus.ACTIVE:
            return False

        return user_id in [chat.client_id, chat.agent_id]

    @database_sync_to_async
    def create_message(self, chat_id, sender_id, content):
        chat = Chat.objects.get(id=chat_id)

        message = Message.objects.create(
            chat=chat,
            sender_id=sender_id,
            content=content,
            isRead=False,
        )

        return {
            "id": message.id,
            "content": message.content,
            "sentAt": message.sentAt.isoformat(),
            "isRead": message.isRead,
            "chat": message.chat_id,
            "sender": message.sender_id,
        }

    @database_sync_to_async
    def mark_message_as_read(self, message_id, reader_id):
        try:
            message = Message.objects.select_related("chat").get(
                id=message_id,
                chat_id=self.chat_id,
            )
        except Message.DoesNotExist:
            return False

        if reader_id not in [message.chat.client_id, message.chat.agent_id]:
            return False

        if message.sender_id == reader_id:
            return False

        if not message.isRead:
            message.isRead = True
            message.save(update_fields=["isRead"])
            return True

        return False

    @database_sync_to_async
    def get_chat_participant_ids(self, chat_id):
        try:
            chat = Chat.objects.get(id=chat_id)
        except Chat.DoesNotExist:
            return []

        return [chat.client_id, chat.agent_id]

    async def broadcast_chat_list_update(self, chat_id, action):
        participant_ids = await self.get_chat_participant_ids(chat_id)

        for user_id in participant_ids:
            await self.channel_layer.group_send(
                f"user_chats_{user_id}",
                {
                    "type": "chat_list_updated",
                    "chat_id": int(chat_id),
                    "action": action,
                },
            )