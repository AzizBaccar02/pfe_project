"""Activate local subscription rows from Stripe (append-only history)."""

from datetime import datetime, timedelta, timezone as datetime_timezone

import stripe
from django.conf import settings

from subscriptions.models import (
    Plan,
    PlanPeriod,
    PlanType,
    Subscription,
    SubscriptionStatus,
)
from subscriptions.services.subscription_repository import (
    apply_subscription_data,
    create_pending_subscription,
    find_by_checkout_session,
    find_by_checkout_session_id,
    find_by_stripe_subscription_id,
    get_current_subscription,
    supersede_previous_active,
)

stripe.api_key = settings.STRIPE_SECRET_KEY


def _stripe_value(obj, key, default=None):
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    try:
        return obj[key]
    except Exception:
        pass

    try:
        return getattr(obj, key)
    except Exception:
        return default


def _stripe_timestamp_to_datetime(timestamp):
    if not timestamp:
        return None

    try:
        return datetime.fromtimestamp(timestamp, tz=datetime_timezone.utc)
    except Exception:
        return None


def _map_stripe_subscription_status(stripe_status):
    status_map = {
        "incomplete": SubscriptionStatus.INCOMPLETE,
        "active": SubscriptionStatus.ACTIVE,
        "trialing": SubscriptionStatus.ACTIVE,
        "past_due": SubscriptionStatus.PAST_DUE,
        "canceled": SubscriptionStatus.CANCELED,
        "unpaid": SubscriptionStatus.UNPAID,
        "incomplete_expired": SubscriptionStatus.EXPIRED,
    }

    return status_map.get(stripe_status, SubscriptionStatus.INCOMPLETE)


def _get_subscription_period_dates(stripe_subscription):
    top_level_start = _stripe_value(stripe_subscription, "current_period_start")
    top_level_end = _stripe_value(stripe_subscription, "current_period_end")

    if top_level_start and top_level_end:
        return top_level_start, top_level_end

    items = _stripe_value(stripe_subscription, "items", {}) or {}
    item_data = _stripe_value(items, "data", []) or []

    period_starts = []
    period_ends = []

    for item in item_data:
        item_start = _stripe_value(item, "current_period_start")
        item_end = _stripe_value(item, "current_period_end")

        if item_start:
            period_starts.append(item_start)

        if item_end:
            period_ends.append(item_end)

    if period_starts and period_ends:
        return min(period_starts), max(period_ends)

    return None, None


def _normalize_period_dates(plan, start_date, end_date):
    if start_date is None:
        return start_date, end_date

    if end_date and end_date > start_date:
        return start_date, end_date

    if plan and plan.planType == PlanType.DATE:
        days = 365 if plan.period == PlanPeriod.YEARLY else 30
        return start_date, start_date + timedelta(days=days)

    return start_date, end_date


def _apply_plan_usage_data(subscription_data, plan, initialize_usage=False):
    if not plan:
        return subscription_data

    if plan.planType == PlanType.USAGE:
        if initialize_usage:
            subscription_data["usageLimit"] = plan.usageLimit
            subscription_data["remainingUsageCount"] = plan.usageLimit
            subscription_data["usedUsageCount"] = 0

    elif plan.planType == PlanType.DATE:
        subscription_data["usageLimit"] = 0
        subscription_data["remainingUsageCount"] = 0
        subscription_data["usedUsageCount"] = 0

    return subscription_data


def _resolve_user_id_from_stripe_subscription(stripe_subscription, fallback_user_id=None):
    metadata = _stripe_value(stripe_subscription, "metadata", {}) or {}
    user_id = _stripe_value(metadata, "user_id")

    if user_id:
        return int(user_id)

    if fallback_user_id:
        return int(fallback_user_id)

    customer_id = _stripe_value(stripe_subscription, "customer")
    if customer_id:
        try:
            customer = stripe.Customer.retrieve(customer_id)
            customer_email = _stripe_value(customer, "email")
            if customer_email:
                from django.contrib.auth import get_user_model

                matched_user = (
                    get_user_model()
                    .objects.filter(email__iexact=customer_email)
                    .first()
                )
                if matched_user:
                    return matched_user.id
        except Exception:
            pass

    return None


def _create_subscription_row(*, user_id, subscription_data):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.filter(pk=user_id).first()
    if user is None:
        return None

    return Subscription.objects.create(user=user, **subscription_data)


def _resolve_target_subscription(
    *,
    user,
    checkout_session_id,
    stripe_subscription_id,
    preferred=None,
):
    """
    Pick which DB row to update.

    - Checkout completion: match the INCOMPLETE row for this session id.
    - Stripe sync/webhooks: match by stripe subscription id only.
    - Otherwise return None so callers create a new history row.
    """
    if preferred is not None:
        return preferred

    if checkout_session_id:
        by_checkout = find_by_checkout_session_id(checkout_session_id)
        if by_checkout is not None:
            return by_checkout

    if stripe_subscription_id:
        return find_by_stripe_subscription_id(stripe_subscription_id)

    return None


def sync_subscription_from_stripe(stripe_subscription, *, fallback_user_id=None):
    """
    Update the row that matches this Stripe subscription id, or create a new
    history row when Stripe reports a brand-new subscription.
    """
    stripe_subscription_id = _stripe_value(stripe_subscription, "id")
    metadata = _stripe_value(stripe_subscription, "metadata", {}) or {}

    user_id = _resolve_user_id_from_stripe_subscription(
        stripe_subscription,
        fallback_user_id=fallback_user_id,
    )

    by_stripe = find_by_stripe_subscription_id(stripe_subscription_id)

    if not user_id and by_stripe:
        user_id = by_stripe.user_id

    plan_id = _stripe_value(metadata, "plan_id")
    if not plan_id and by_stripe and by_stripe.plan_id:
        plan_id = by_stripe.plan_id

    if not user_id:
        return None

    user_id = int(user_id)

    from django.contrib.auth import get_user_model

    user = get_user_model().objects.filter(pk=user_id).first()
    if user is None:
        return None

    target_subscription = _resolve_target_subscription(
        user=user,
        checkout_session_id=None,
        stripe_subscription_id=stripe_subscription_id,
    )

    plan = Plan.objects.filter(id=plan_id).first() if plan_id else None

    stripe_status = _stripe_value(stripe_subscription, "status")
    local_status = _map_stripe_subscription_status(stripe_status)

    period_start, period_end = _get_subscription_period_dates(stripe_subscription)
    start_date = _stripe_timestamp_to_datetime(period_start)
    end_date = _stripe_timestamp_to_datetime(period_end)
    start_date, end_date = _normalize_period_dates(plan, start_date, end_date)

    subscription_data = {
        "status": local_status,
        "isActive": local_status == SubscriptionStatus.ACTIVE,
        "stripeCustomerId": _stripe_value(stripe_subscription, "customer"),
        "stripeSubscriptionId": stripe_subscription_id,
        "startDate": start_date,
        "endDate": end_date,
        "cancelAtPeriodEnd": _stripe_value(
            stripe_subscription,
            "cancel_at_period_end",
            False,
        ),
    }

    if plan_id:
        subscription_data["plan_id"] = plan_id

    should_initialize_usage = (
        local_status == SubscriptionStatus.ACTIVE
        and plan is not None
        and plan.planType == PlanType.USAGE
        and (
            target_subscription is None
            or target_subscription.status != SubscriptionStatus.ACTIVE
            or (
                target_subscription.usageLimit == 0
                and target_subscription.remainingUsageCount == 0
                and target_subscription.usedUsageCount == 0
            )
        )
    )

    subscription_data = _apply_plan_usage_data(
        subscription_data=subscription_data,
        plan=plan,
        initialize_usage=should_initialize_usage,
    )

    if target_subscription:
        subscription = apply_subscription_data(target_subscription, subscription_data)
    else:
        subscription = _create_subscription_row(
            user_id=user_id,
            subscription_data=subscription_data,
        )

    if subscription and subscription.status == SubscriptionStatus.ACTIVE:
        supersede_previous_active(user, subscription.pk)

    return subscription


def complete_checkout_session(checkout_session):
    """
    Activate the pending row created for this checkout session.
    Never overwrites older subscription rows for the same user.
    """
    checkout_session_id = _stripe_value(checkout_session, "id")
    metadata = _stripe_value(checkout_session, "metadata", {}) or {}

    user_id = _stripe_value(metadata, "user_id")
    plan_id = _stripe_value(metadata, "plan_id")

    stripe_subscription_id = _stripe_value(checkout_session, "subscription")
    stripe_customer_id = _stripe_value(checkout_session, "customer")
    transaction_id = _stripe_value(checkout_session, "payment_intent")

    from django.contrib.auth import get_user_model

    user = None
    if user_id:
        user = get_user_model().objects.filter(pk=int(user_id)).first()

    if not user_id:
        pending = find_by_checkout_session_id(checkout_session_id)
        if pending is not None:
            user_id = pending.user_id
            user = pending.user

    if not user_id or user is None:
        raise ValueError("Could not resolve user for this checkout session.")

    user_id = int(user_id)

    if user is None:
        user = get_user_model().objects.filter(pk=user_id).first()

    if user is None:
        raise ValueError("Could not resolve user for this checkout session.")

    target_subscription = _resolve_target_subscription(
        user=user,
        checkout_session_id=checkout_session_id,
        stripe_subscription_id=None,
    )

    if not plan_id and target_subscription and target_subscription.plan_id:
        plan_id = target_subscription.plan_id

    plan = Plan.objects.filter(id=plan_id).first() if plan_id else None

    local_status = SubscriptionStatus.ACTIVE
    start_date = None
    end_date = None

    if stripe_subscription_id:
        if isinstance(stripe_subscription_id, str):
            stripe_subscription = stripe.Subscription.retrieve(
                stripe_subscription_id,
                expand=["items.data.price"],
            )
        else:
            stripe_subscription = stripe_subscription_id
            stripe_subscription_id = _stripe_value(stripe_subscription, "id")

        stripe_status = _stripe_value(stripe_subscription, "status")
        local_status = _map_stripe_subscription_status(stripe_status)

        period_start, period_end = _get_subscription_period_dates(stripe_subscription)
        start_date = _stripe_timestamp_to_datetime(period_start)
        end_date = _stripe_timestamp_to_datetime(period_end)
        start_date, end_date = _normalize_period_dates(plan, start_date, end_date)

        if not stripe_customer_id:
            stripe_customer_id = _stripe_value(stripe_subscription, "customer")

    if target_subscription is None:
        target_subscription = _resolve_target_subscription(
            user=user,
            checkout_session_id=checkout_session_id,
            stripe_subscription_id=stripe_subscription_id,
        )

    subscription_data = {
        "plan_id": plan_id,
        "status": local_status,
        "isActive": local_status == SubscriptionStatus.ACTIVE,
        "stripeCustomerId": stripe_customer_id,
        "stripeSubscriptionId": stripe_subscription_id,
        "stripeCheckoutSessionId": checkout_session_id,
        "transactionId": transaction_id,
        "startDate": start_date,
        "endDate": end_date,
    }

    subscription_data = _apply_plan_usage_data(
        subscription_data=subscription_data,
        plan=plan,
        initialize_usage=True,
    )

    if target_subscription:
        subscription = apply_subscription_data(target_subscription, subscription_data)
    else:
        subscription = _create_subscription_row(
            user_id=user_id,
            subscription_data=subscription_data,
        )

    if subscription and subscription.status == SubscriptionStatus.ACTIVE:
        supersede_previous_active(user, subscription.pk)

    return subscription


def sync_subscription_for_user(user, session_id=None):
    """
    Activate the subscription tied to a checkout session, or the newest
    Stripe subscription for this user.
    """
    session_ids_to_try = []
    explicit_session = (session_id or "").strip()

    if explicit_session:
        session_ids_to_try.append(explicit_session)

    pending_rows = (
        Subscription.objects.filter(
            user=user,
            status=SubscriptionStatus.INCOMPLETE,
        )
        .order_by("-createdAt")
    )

    for pending_row in pending_rows:
        stored_id = (pending_row.stripeCheckoutSessionId or "").strip()
        if stored_id and stored_id not in session_ids_to_try:
            session_ids_to_try.append(stored_id)

    for checkout_id in session_ids_to_try:
        try:
            checkout_session = retrieve_checkout_session(checkout_id)
            checkout_status = _stripe_value(checkout_session, "status")
            payment_status = _stripe_value(checkout_session, "payment_status")

            if checkout_status == "complete" or payment_status in (
                "paid",
                "no_payment_required",
            ):
                synced = complete_checkout_session(checkout_session)
                if synced and synced.can_use_subscription:
                    return synced
        except Exception:
            continue

    try:
        customers = stripe.Customer.list(email=user.email, limit=10)
        for customer in _stripe_value(customers, "data", []) or []:
            customer_id = _stripe_value(customer, "id")
            if not customer_id:
                continue

            stripe_subs = _stripe_value(
                stripe.Subscription.list(customer=customer_id, limit=10),
                "data",
                [],
            ) or []

            for stripe_sub in sorted(
                stripe_subs,
                key=lambda item: _stripe_value(item, "created", 0),
                reverse=True,
            ):
                stripe_sub_id = _stripe_value(stripe_sub, "id")
                stripe_status = _stripe_value(stripe_sub, "status")
                if stripe_status not in ("active", "trialing"):
                    continue

                existing = find_by_stripe_subscription_id(stripe_sub_id)
                if (
                    existing is not None
                    and existing.status == SubscriptionStatus.ACTIVE
                    and existing.can_use_subscription
                ):
                    continue

                synced = sync_subscription_from_stripe(
                    stripe_sub,
                    fallback_user_id=user.id,
                )
                if synced and synced.can_use_subscription:
                    return synced
    except Exception:
        pass

    current = get_current_subscription(user)
    if current and current.can_use_subscription and not explicit_session:
        return current

    if current:
        return current

    raise ValueError(
        "No completed Stripe payment was found for your account. "
        "Please finish checkout or contact support."
    )


def retrieve_checkout_session(session_id):
    return stripe.checkout.Session.retrieve(
        session_id,
        expand=["subscription"],
    )
