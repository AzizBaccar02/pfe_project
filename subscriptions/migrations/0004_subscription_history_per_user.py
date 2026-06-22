# Allow multiple subscription rows per user (billing history).

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0003_plan_plantype_plan_targetrole"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="subscription",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="subscriptions",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="stripeSubscriptionId",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="stripeCheckoutSessionId",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                unique=True,
            ),
        ),
        migrations.AlterModelOptions(
            name="subscription",
            options={"ordering": ["-createdAt"]},
        ),
    ]
