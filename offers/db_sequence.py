"""Reset PostgreSQL sequences when manual imports desync primary keys."""

from django.db import connection


def reset_images_pk_sequence() -> None:
    if connection.vendor != "postgresql":
        return

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT setval(
                pg_get_serial_sequence('offers_images', 'id'),
                COALESCE((SELECT MAX(id) FROM offers_images), 1),
                true
            );
            """
        )
