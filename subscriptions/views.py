from datetime import datetime, timezone as datetime_timezone

import stripe

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Plan, PlanType, Subscription, SubscriptionStatus
from .serializers import PlanSerializer, SubscriptionSerializer
from .services.stripe_service import (
    create_checkout_session,
    create_customer_portal_session,
)


class PlanListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plans = (
            Plan.objects
            .filter(isActive=True, targetRole=request.user.role)
            .order_by("price")
        )

        serializer = PlanSerializer(plans, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MySubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subscription = (
            Subscription.objects
            .filter(user=request.user)
            .select_related("plan")
            .first()
        )

        if not subscription:
            return Response(
                {
                    "hasActiveSubscription": False,
                    "subscription": None,
                    "message": "No subscription found for this user.",
                },
                status=status.HTTP_200_OK,
            )

        serializer = SubscriptionSerializer(subscription)

        return Response(
            {
                "hasActiveSubscription": subscription.has_active_subscription,
                "subscription": serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get("planId")

        if not plan_id:
            return Response(
                {"detail": "planId is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            plan = Plan.objects.get(id=plan_id, isActive=True)
        except Plan.DoesNotExist:
            return Response(
                {"detail": "Plan not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if plan.targetRole != request.user.role:
            return Response(
                {"detail": "This plan is not available for your role."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            checkout_session = create_checkout_session(
                user=request.user,
                plan=plan,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription, _ = Subscription.objects.update_or_create(
            user=request.user,
            defaults={
                "plan": plan,
                "status": SubscriptionStatus.INCOMPLETE,
                "isActive": False,
                "stripeCheckoutSessionId": checkout_session.id,
            },
        )

        return Response(
            {
                "checkoutUrl": checkout_session.url,
                "sessionId": checkout_session.id,
                "subscriptionId": subscription.id,
            },
            status=status.HTTP_200_OK,
        )


class CreateCustomerPortalSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subscription = (
            Subscription.objects
            .filter(user=request.user)
            .select_related("plan")
            .first()
        )

        if not subscription:
            return Response(
                {"detail": "No subscription found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not subscription.stripeCustomerId:
            return Response(
                {"detail": "Stripe customer ID not found for this subscription."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            portal_session = create_customer_portal_session(
                customer_id=subscription.stripeCustomerId,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "portalUrl": portal_session.url,
            },
            status=status.HTTP_200_OK,
        )


def subscription_success_view(request):
    return HttpResponse("""
        <h1>Payment successful</h1>
        <p>Your payment was completed successfully.</p>
        <p>You can close this page and go back to JobMatch.</p>
    """)


def subscription_cancel_view(request):
    return HttpResponse("""
        <h1>Payment canceled</h1>
        <p>Your payment was canceled.</p>
        <p>You can go back and try again.</p>
    """)


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


def _sync_subscription_from_stripe(stripe_subscription):
    stripe_subscription_id = _stripe_value(stripe_subscription, "id")
    metadata = _stripe_value(stripe_subscription, "metadata", {}) or {}

    user_id = _stripe_value(metadata, "user_id")
    plan_id = _stripe_value(metadata, "plan_id")

    existing_subscription = None

    if stripe_subscription_id:
        existing_subscription = (
            Subscription.objects
            .filter(stripeSubscriptionId=stripe_subscription_id)
            .select_related("plan", "user")
            .first()
        )

    if not user_id and existing_subscription:
        user_id = existing_subscription.user_id

    if not plan_id and existing_subscription and existing_subscription.plan_id:
        plan_id = existing_subscription.plan_id

    if not user_id:
        return

    plan = None
    if plan_id:
        plan = Plan.objects.filter(id=plan_id).first()

    stripe_status = _stripe_value(stripe_subscription, "status")
    local_status = _map_stripe_subscription_status(stripe_status)

    period_start, period_end = _get_subscription_period_dates(stripe_subscription)

    subscription_data = {
        "status": local_status,
        "isActive": local_status == SubscriptionStatus.ACTIVE,
        "stripeCustomerId": _stripe_value(stripe_subscription, "customer"),
        "stripeSubscriptionId": stripe_subscription_id,
        "startDate": _stripe_timestamp_to_datetime(period_start),
        "endDate": _stripe_timestamp_to_datetime(period_end),
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
            not existing_subscription
            or existing_subscription.status != SubscriptionStatus.ACTIVE
            or (
                existing_subscription.usageLimit == 0
                and existing_subscription.remainingUsageCount == 0
                and existing_subscription.usedUsageCount == 0
            )
        )
    )

    subscription_data = _apply_plan_usage_data(
        subscription_data=subscription_data,
        plan=plan,
        initialize_usage=should_initialize_usage,
    )

    Subscription.objects.update_or_create(
        user_id=user_id,
        defaults=subscription_data,
    )


@csrf_exempt
def stripe_webhook_view(request):
    payload = request.body
    signature_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not settings.STRIPE_WEBHOOK_SECRET:
        return JsonResponse(
            {"detail": "Stripe webhook secret is not configured."},
            status=400,
        )

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except ValueError:
        return JsonResponse({"detail": "Invalid payload."}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({"detail": "Invalid signature."}, status=400)

    try:
        event_type = _stripe_value(event, "type")
        data = _stripe_value(event, "data", {})
        data_object = _stripe_value(data, "object", {})

        if event_type == "checkout.session.completed":
            checkout_session = data_object

            metadata = _stripe_value(checkout_session, "metadata", {}) or {}
            user_id = _stripe_value(metadata, "user_id")
            plan_id = _stripe_value(metadata, "plan_id")

            stripe_subscription_id = _stripe_value(checkout_session, "subscription")
            stripe_customer_id = _stripe_value(checkout_session, "customer")

            if user_id:
                plan = None
                if plan_id:
                    plan = Plan.objects.filter(id=plan_id).first()

                subscription_data = {
                    "status": SubscriptionStatus.ACTIVE,
                    "isActive": True,
                    "stripeCustomerId": stripe_customer_id,
                    "stripeSubscriptionId": stripe_subscription_id,
                    "stripeCheckoutSessionId": _stripe_value(checkout_session, "id"),
                    "transactionId": _stripe_value(checkout_session, "payment_intent"),
                }

                if plan_id:
                    subscription_data["plan_id"] = plan_id

                subscription_data = _apply_plan_usage_data(
                    subscription_data=subscription_data,
                    plan=plan,
                    initialize_usage=True,
                )

                Subscription.objects.update_or_create(
                    user_id=user_id,
                    defaults=subscription_data,
                )

                if stripe_subscription_id:
                    try:
                        stripe_subscription = stripe.Subscription.retrieve(
                            stripe_subscription_id,
                            expand=["items.data.price"],
                        )
                        _sync_subscription_from_stripe(stripe_subscription)
                    except Exception as stripe_error:
                        print("Stripe subscription retrieve error:", stripe_error)

        elif event_type in [
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ]:
            try:
                _sync_subscription_from_stripe(data_object)
            except Exception as sync_error:
                print("Stripe subscription sync error:", sync_error)

        elif event_type == "invoice.paid":
            stripe_subscription_id = _stripe_value(data_object, "subscription")

            if stripe_subscription_id:
                try:
                    stripe_subscription = stripe.Subscription.retrieve(
                        stripe_subscription_id,
                        expand=["items.data.price"],
                    )
                    _sync_subscription_from_stripe(stripe_subscription)
                except Exception as stripe_error:
                    print("Stripe invoice paid sync error:", stripe_error)

        elif event_type == "invoice.payment_failed":
            stripe_subscription_id = _stripe_value(data_object, "subscription")

            if stripe_subscription_id:
                Subscription.objects.filter(
                    stripeSubscriptionId=stripe_subscription_id
                ).update(
                    status=SubscriptionStatus.PAST_DUE,
                    isActive=False,
                )

        return JsonResponse({"received": True})

    except Exception as e:
        print("Stripe webhook error:", e)
        return JsonResponse(
            {
                "detail": "Webhook received but processing failed.",
                "error": str(e),
            },
            status=500,
        )