from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),  # adjust if your last migration has a different name
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name="notification",
            name="type",
            field=models.CharField(
                choices=[
                    ("PROPOSAL_STATUS",   "Proposal Status"),
                    ("NEW_MESSAGE",       "New Message"),
                    ("MATCH_CREATED",     "Match Created"),
                    ("AGENT_LIKED_OFFER", "Agent Liked Offer"),
                    ("CLIENT_REJECTED",   "Client Rejected"),
                ],
                max_length=30,
            ),
        ),
    ]