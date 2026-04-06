import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from django.contrib.auth import get_user_model
from chats.models import Chat, Message, ChatStatus

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
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

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get("content", "").strip()

        if not content:
            await self.send(text_data=json.dumps({
                "error": "content is required"
            }))
            return

        allowed = await self.user_can_access_chat(self.user.id, self.chat_id)
        if not allowed:
            await self.send(text_data=json.dumps({
                "error": "You are not allowed to send messages in this chat"
            }))
            return

        message_data = await self.create_message(
            chat_id=self.chat_id,
            sender_id=self.user.id,
            content=content,
        )

        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat_message",
                "message": message_data,
            }
        )

    async def chat_message(self, event):
        message = event["message"]

        await self.send(text_data=json.dumps({
            "type": "new_message",
            "message": message,
        }))

        # If this connected user is the receiver, mark message as seen automatically
        if message["sender"] != self.user.id:
            updated = await self.mark_message_as_read(message["id"], self.user.id)

            if updated:
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "message_seen",
                        "message_id": message["id"],
                        "reader_id": self.user.id,
                    }
                )

    async def message_seen(self, event):
        await self.send(text_data=json.dumps({
            "type": "message_seen",
            "message_id": event["message_id"],
            "reader_id": event["reader_id"],
        }))

    async def get_user_from_jwt(self):
        try:
            query_string = self.scope["query_string"].decode()
            query_params = parse_qs(query_string)
            token = query_params.get("token", [None])[0]

            if not token:
                return None

            validated_token = UntypedToken(token)
            user = await self.get_user(validated_token)
            return user
        except (InvalidToken, TokenError, Exception):
            return None

    @database_sync_to_async
    def get_user(self, validated_token):
        from rest_framework_simplejwt.backends import TokenBackend
        from django.conf import settings

        token_backend = TokenBackend(
            algorithm="HS256",
            signing_key=settings.SECRET_KEY
        )
        decoded_data = token_backend.decode(validated_token.token, verify=True)
        user_id = decoded_data.get("user_id")

        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

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
                chat_id=self.chat_id
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