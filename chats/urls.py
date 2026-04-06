from django.urls import path
from .views import (
    create_chat,
    list_chats,
    get_chat_by_id,
    update_chat,
    delete_chat,
    create_message,
    get_messages_by_chat_id,
    update_message,
    delete_message,
    mark_all_messages_as_read,
    close_chat,
)

urlpatterns = [
    # Chat CRUD
    path("chats/create/", create_chat, name="create-chat"),
    path("chats/list/", list_chats, name="list-chats"),
    path("chats/<int:chat_id>/", get_chat_by_id, name="get-chat-by-id"),
    path("chats/<int:chat_id>/update/", update_chat, name="update-chat"),
    path("chats/<int:chat_id>/delete/", delete_chat, name="delete-chat"),

    # Message CRUD
    path("chats/<int:chat_id>/messages/create/", create_message, name="create-message"),
    path("chats/<int:chat_id>/messages/", get_messages_by_chat_id, name="get-messages-by-chat-id"),
    path("chats/<int:chat_id>/messages/<int:message_id>/update/", update_message, name="update-message"),
    path("chats/<int:chat_id>/messages/<int:message_id>/delete/", delete_message, name="delete-message"),

    # Extra actions
    path("chats/<int:chat_id>/messages/read-all/", mark_all_messages_as_read, name="mark-all-messages-as-read"),
    path("chats/<int:chat_id>/close/", close_chat, name="close-chat"),
]