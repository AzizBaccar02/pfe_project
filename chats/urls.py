from django.urls import path

from .views import (
    close_chat,
    create_chat,
    create_message,
    delete_chat,
    delete_message,
    get_chat_by_id,
    get_messages_by_chat_id,
    list_chats,
    mark_all_messages_as_read,
    update_chat,
    update_message,
)

urlpatterns = [
    # Chat CRUD
    path("chats/create/", create_chat, name="create-chat"),
    path("chats/list/", list_chats, name="list-chats"),
    path("chats/<int:chat_id>/", get_chat_by_id, name="get-chat-by-id"),
    path("chats/<int:chat_id>/update/", update_chat, name="update-chat"),
    path("chats/<int:chat_id>/delete/", delete_chat, name="delete-chat"),

    # Message CRUD
    path(
        "chats/<int:chat_id>/messages/create/",
        create_message,
        name="create-message",
    ),
    path(
        "chats/<int:chat_id>/messages/",
        get_messages_by_chat_id,
        name="get-messages-by-chat-id",
    ),
    path(
        "chats/<int:chat_id>/messages/<int:message_id>/update/",
        update_message,
        name="update-message",
    ),
    path(
        "chats/<int:chat_id>/messages/<int:message_id>/delete/",
        delete_message,
        name="delete-message",
    ),

    # Extra actions
    path(
        "chats/<int:chat_id>/messages/read-all/",
        mark_all_messages_as_read,
        name="mark-all-messages-as-read",
    ),
    path("chats/<int:chat_id>/close/", close_chat, name="close-chat"),
]