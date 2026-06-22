from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("offers", "0003_images"),
    ]

    operations = [
        migrations.AlterField(
            model_name="category",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
    ]
