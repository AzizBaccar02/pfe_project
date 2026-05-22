# chats/presence.py

from threading import Lock

_online_user_connection_counts = {}
_presence_lock = Lock()


def mark_user_connected(user_id):
    user_id = int(user_id)

    with _presence_lock:
        previous_count = _online_user_connection_counts.get(user_id, 0)
        _online_user_connection_counts[user_id] = previous_count + 1

        return previous_count == 0


def mark_user_disconnected(user_id):
    user_id = int(user_id)

    with _presence_lock:
        previous_count = _online_user_connection_counts.get(user_id, 0)

        if previous_count <= 1:
            _online_user_connection_counts.pop(user_id, None)
            return True

        _online_user_connection_counts[user_id] = previous_count - 1
        return False


def is_user_online(user_id):
    if not user_id:
        return False

    user_id = int(user_id)

    with _presence_lock:
        return _online_user_connection_counts.get(user_id, 0) > 0