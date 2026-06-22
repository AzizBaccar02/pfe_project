#C:\Users\Lenovo\django_project\pfe_project2\pfe_project\subscriptions\management\commands\expire_date_subscriptions.py
from django.core.management.base import BaseCommand
from django.utils import timezone

from subscriptions.models import Subscription, SubscriptionStatus


class Command(BaseCommand):
    help = "Expire subscriptions whose endDate has passed."

    def handle(self, *args, **options):
        now = timezone.now()
        expired_count = 0

        candidates = Subscription.objects.filter(
            status=SubscriptionStatus.ACTIVE,
            isActive=True,
            endDate__lt=now,
        )

        for subscription in candidates.iterator():
            if subscription.sync_expired_state(save=True):
                expired_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {expired_count} date-based subscriptions."
            )
        )