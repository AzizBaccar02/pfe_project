#subscriptions\services\usage_service.py

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from subscriptions.models import PlanType, Subscription, SubscriptionStatus
from subscriptions.services.subscription_repository import (
    get_current_subscription,
    subscription_blocks_free_tier,
    user_blocked_from_free_tier,
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

    return subscription.sync_expired_state(save=True)


def resolve_create_offer_access(user, subscription, free_usage_remaining):
    """
    Shared rules for API responses and offer creation enforcement.
    Returns (allowed, message).
    """
    if subscription:
        subscription.sync_expired_state()
        subscription.refresh_from_db()

        if subscription.has_active_subscription:
            plan = subscription.plan
            if (
                plan
                and plan.planType == PlanType.USAGE
                and subscription.remainingUsageCount <= 0
            ):
                return False, _inactive_subscription_message(subscription)
            return True, None

        if subscription_blocks_free_tier(subscription):
            return False, _inactive_subscription_message(subscription)

    if user_blocked_from_free_tier(user):
        return False, "Your subscription is not active. Please renew to continue."

    if free_usage_remaining <= 0:
        return False, (
            "You have used all your free tries. Please subscribe to continue."
        )

    return True, None


def _inactive_subscription_message(subscription):
    if not subscription.is_within_billing_window():
        if subscription.startDate:
            now = timezone.now()
            start_date = subscription._aware_datetime(subscription.startDate)
            if start_date and now < start_date:
                return "Your subscription has not started yet."

        return "Your subscription has expired. Please renew to continue."

    if (
        subscription.plan
        and subscription.plan.planType == PlanType.USAGE
        and subscription.remainingUsageCount <= 0
    ):
        return "You have reached your subscription usage limit. Please renew to continue."

    return "Your subscription is not active. Please renew to continue."


def _consume_free_usage(locked_user):
    if locked_user.remainingFreeUsageCount <= 0:
        return None

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
        "remainingFreeUsageCount": locked_user.remainingFreeUsageCount,
        "usedFreeUsageCount": locked_user.usedFreeUsageCount,
    }


def _consume_subscription_quota(subscription):
    plan = subscription.plan

    if not plan:
        raise PermissionDenied("Subscription plan not found.")

    if plan.planType == PlanType.DATE:
        return {
            "source": "subscription_date",
            "subscription": subscription,
            "remainingFreeUsageCount": None,
            "usedFreeUsageCount": None,
        }

    if plan.planType == PlanType.USAGE:
        if subscription.remainingUsageCount <= 0:
            return None

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
            "remainingFreeUsageCount": None,
            "usedFreeUsageCount": None,
            "remainingSubscriptionUsageCount": subscription.remainingUsageCount,
            "usedSubscriptionUsageCount": subscription.usedUsageCount,
        }

    return None


@transaction.atomic
def consume_subscription_usage(user, action):
    """
    Consume one usage unit for an action.

    Priority:
    1. Active paid subscription (USAGE quota or unlimited DATE plan)
    2. Free tier counters on the user row
    3. PermissionDenied
    """
    User = get_user_model()

    locked_user = (
        User.objects
        .select_for_update()
        .get(id=user.id)
    )

    required_role = ACTION_REQUIRED_ROLE.get(action)

    if required_role and locked_user.role != required_role:
        raise PermissionDenied("Your role is not allowed to perform this action.")

    current = get_current_subscription(locked_user)
    subscription = None
    if current is not None:
        subscription = (
            Subscription.objects
            .select_for_update(of=("self",))
            .select_related("plan")
            .filter(pk=current.pk)
            .first()
        )

    if subscription:
        _expire_subscription_if_needed(subscription)
        subscription.refresh_from_db()

        allowed, denial_message = resolve_create_offer_access(
            locked_user,
            subscription,
            locked_user.remainingFreeUsageCount,
        )

        if not allowed:
            raise PermissionDenied(denial_message)

        if subscription.has_active_subscription:
            plan = subscription.plan

            if not plan:
                raise PermissionDenied("Subscription plan not found.")

            if plan.targetRole != locked_user.role:
                raise PermissionDenied(
                    "This subscription plan does not match your role."
                )

            usage_result = _consume_subscription_quota(subscription)

            if usage_result is not None:
                usage_result["remainingFreeUsageCount"] = (
                    locked_user.remainingFreeUsageCount
                )
                usage_result["usedFreeUsageCount"] = locked_user.usedFreeUsageCount
                return usage_result

            raise PermissionDenied(_inactive_subscription_message(subscription))

    free_usage_result = _consume_free_usage(locked_user)

    if free_usage_result is not None:
        return free_usage_result

    raise PermissionDenied(
        "You have used all your free tries. Please subscribe to continue."
    )
