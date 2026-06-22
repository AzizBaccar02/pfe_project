from django.db import connection, migrations


def fix_images_sequence(apps, schema_editor):
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


class Migration(migrations.Migration):

    dependencies = [
        ("offers", "0004_category_description_optional"),
    ]

    operations = [
        migrations.RunPython(fix_images_sequence, migrations.RunPython.noop),
    ]
