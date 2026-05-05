from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from subscriptions.models import (
    PlanType,
    Subscription,
    SubscriptionStatus,
)
from users.models import Role


class SubscriptionUsageAction:
    CREATE_OFFER = "CREATE_OFFER"
    LIKE_OFFER = "LIKE_OFFER"


ACTION_REQUIRED_ROLE = {
    SubscriptionUsageAction.CREATE_OFFER: Role.CLIENT,
    SubscriptionUsageAction.LIKE_OFFER: Role.AGENT,
}


def _expire_subscription_if_needed(subscription):
    if not subscription:
        return False

    plan = subscription.plan

    if (
        subscription.status == SubscriptionStatus.ACTIVE
        and subscription.isActive
        and plan
        and plan.planType == PlanType.DATE
        and subscription.endDate
        and timezone.now() > subscription.endDate
    ):
        subscription.status = SubscriptionStatus.EXPIRED
        subscription.isActive = False
        subscription.save(
            update_fields=[
                "status",
                "isActive",
                "updatedAt",
            ]
        )
        return True

    return False


@transaction.atomic
def consume_subscription_usage(user, action):
    User = get_user_model()

    locked_user = (
        User.objects
        .select_for_update()
        .get(id=user.id)
    )

    required_role = ACTION_REQUIRED_ROLE.get(action)

    if required_role and locked_user.role != required_role:
        raise PermissionDenied("Your role is not allowed to perform this action.")

    subscription = (
        Subscription.objects
        .select_for_update()
        .filter(user=locked_user)
        .first()
    )

    if subscription:
        was_expired = _expire_subscription_if_needed(subscription)

        if was_expired:
            raise PermissionDenied(
                "Your subscription has expired. Please renew your subscription."
            )

        if subscription.status == SubscriptionStatus.ACTIVE and subscription.isActive:
            plan = subscription.plan

            if not plan:
                raise PermissionDenied("Subscription plan not found.")

            if plan.targetRole != locked_user.role:
                raise PermissionDenied(
                    "This subscription plan does not match your role."
                )

            if plan.planType == PlanType.DATE:
                return {
                    "source": "subscription_date",
                    "subscription": subscription,
                }

            if plan.planType == PlanType.USAGE:
                if subscription.remainingUsageCount <= 0:
                    raise PermissionDenied(
                        "You have no remaining subscription uses. Please renew your subscription."
                    )

                subscription.remainingUsageCount -= 1
                subscription.usedUsageCount += 1
                subscription.save(
                    update_fields=[
                        "remainingUsageCount",
                        "usedUsageCount",
                        "updatedAt",
                    ]
                )

                return {
                    "source": "subscription_usage",
                    "subscription": subscription,
                }

    if locked_user.remainingFreeUsageCount > 0:
        locked_user.remainingFreeUsageCount -= 1
        locked_user.usedFreeUsageCount += 1
        locked_user.save(
            update_fields=[
                "remainingFreeUsageCount",
                "usedFreeUsageCount",
            ]
        )

        return {
            "source": "free_usage",
            "subscription": None,
        }

    raise PermissionDenied(
        "You have used all your free tries. Please subscribe to continue."
    )