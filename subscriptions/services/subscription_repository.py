"""One user → many subscription rows (full billing history)."""

from subscriptions.models import Subscription, SubscriptionStatus


def subscriptions_queryset(user):
    return Subscription.objects.filter(user=user).select_related("plan")


def sync_all_expired_for_user(user):
    for subscription in subscriptions_queryset(user):
        subscription.sync_expired_state()


def find_by_checkout_session(user, session_id):
    if not session_id:
        return None

    return (
        subscriptions_queryset(user)
        .filter(stripeCheckoutSessionId=session_id)
        .first()
    )


def find_by_checkout_session_id(session_id):
    if not session_id:
        return None

    return (
        Subscription.objects
        .filter(stripeCheckoutSessionId=session_id)
        .select_related("plan", "user")
        .first()
    )


def latest_pending_subscription(user):
    return (
        subscriptions_queryset(user)
        .filter(status=SubscriptionStatus.INCOMPLETE)
        .order_by("-createdAt")
        .first()
    )


def find_by_stripe_subscription_id(stripe_subscription_id):
    if not stripe_subscription_id:
        return None

    return (
        Subscription.objects
        .filter(stripeSubscriptionId=stripe_subscription_id)
        .select_related("plan", "user")
        .first()
    )


def get_stripe_customer_id(user):
    subscription = (
        subscriptions_queryset(user)
        .exclude(stripeCustomerId__isnull=True)
        .exclude(stripeCustomerId="")
        .order_by("-createdAt")
        .first()
    )
    return subscription.stripeCustomerId if subscription else None


def get_current_subscription(user):
    """
    Subscription used for access checks and the main /me/ payload.
    Prefer the newest usable ACTIVE row, else latest INCOMPLETE checkout.
    """
    sync_all_expired_for_user(user)
    queryset = subscriptions_queryset(user)

    for subscription in queryset.filter(
        status=SubscriptionStatus.ACTIVE,
        isActive=True,
    ).order_by("-startDate", "-createdAt"):
        if subscription.has_active_subscription:
            return subscription

    incomplete = queryset.filter(
        status=SubscriptionStatus.INCOMPLETE,
    ).order_by("-createdAt").first()
    if incomplete is not None:
        return incomplete

    return queryset.order_by("-createdAt").first()


def get_subscription_history(user):
    sync_all_expired_for_user(user)
    return list(subscriptions_queryset(user).order_by("-createdAt"))


def subscription_blocks_free_tier(subscription):
    if subscription.has_active_subscription:
        return False

    if subscription.status == SubscriptionStatus.INCOMPLETE:
        return bool(
            subscription.plan_id
            or subscription.stripeSubscriptionId
            or subscription.stripeCustomerId
        )

    return True


def user_blocked_from_free_tier(user):
    return any(
        subscription_blocks_free_tier(subscription)
        for subscription in subscriptions_queryset(user)
    )


def supersede_previous_active(user, keep_subscription_id):
    """Keep old rows for history; mark previous ACTIVE plans as expired."""
    subscriptions_queryset(user).filter(
        status=SubscriptionStatus.ACTIVE,
        isActive=True,
    ).exclude(pk=keep_subscription_id).update(
        status=SubscriptionStatus.EXPIRED,
        isActive=False,
    )


def create_pending_subscription(
    *,
    user,
    plan,
    checkout_session_id,
    stripe_customer_id=None,
):
    return Subscription.objects.create(
        user=user,
        plan=plan,
        status=SubscriptionStatus.INCOMPLETE,
        isActive=False,
        stripeCheckoutSessionId=checkout_session_id,
        stripeCustomerId=stripe_customer_id or None,
    )


def apply_subscription_data(subscription, data):
    for field, value in data.items():
        setattr(subscription, field, value)
    subscription.save()
    subscription.sync_expired_state()
    subscription.refresh_from_db()
    return subscription
