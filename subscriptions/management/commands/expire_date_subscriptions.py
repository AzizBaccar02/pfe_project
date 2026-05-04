from django.core.management.base import BaseCommand
from django.utils import timezone

from subscriptions.models import PlanType, Subscription, SubscriptionStatus


class Command(BaseCommand):
    help = "Expire date-based subscriptions whose endDate has passed."

    def handle(self, *args, **options):
        now = timezone.now()

        expired_count = (
            Subscription.objects
            .filter(
                status=SubscriptionStatus.ACTIVE,
                isActive=True,
                plan__planType=PlanType.DATE,
                endDate__lt=now,
            )
            .update(
                status=SubscriptionStatus.EXPIRED,
                isActive=False,
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Expired {expired_count} date-based subscriptions."
            )
        )