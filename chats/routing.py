# chats/routing.py

from django.urls import path

from .consumers import ChatConsumer, UserChatsConsumer

websocket_urlpatterns = [
    path("ws/chats/inbox/", UserChatsConsumer.as_asgi()),
    path("ws/chats/<int:chat_id>/", ChatConsumer.as_asgi()),
]