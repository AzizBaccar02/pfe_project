#subscriptions\views.py

import stripe

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Plan, Subscription, SubscriptionStatus
from .serializers import PlanSerializer, SubscriptionSerializer
from .services.checkout_sync import (
    complete_checkout_session,
    sync_subscription_from_stripe,
    sync_subscription_for_user,
)
from .services.subscription_repository import (
    create_pending_subscription,
    get_current_subscription,
    get_stripe_customer_id,
    get_subscription_history,
)
from .services.stripe_service import (
    create_checkout_session,
    create_customer_portal_session,
)
from .services.usage_service import resolve_create_offer_access


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

    def _get_free_usage_data(self, user):
        free_usage_limit = getattr(user, "freeUsageLimit", 0)
        remaining_free_usage_count = getattr(user, "remainingFreeUsageCount", 0)
        used_free_usage_count = getattr(user, "usedFreeUsageCount", 0)

        return {
            "freeUsageLimit": free_usage_limit,
            "remainingFreeUsageCount": remaining_free_usage_count,
            "usedFreeUsageCount": used_free_usage_count,
        }

    def get(self, request):
        subscription = get_current_subscription(request.user)
        history = get_subscription_history(request.user)
        free_usage = self._get_free_usage_data(request.user)

        if not subscription:
            return Response(
                {
                    "hasActiveSubscription": False,
                    "activeUsageSource": "FREE",
                    "canCreateOffer": free_usage["remainingFreeUsageCount"] > 0,
                    "subscription": None,
                    "history": [],
                    "freeUsage": free_usage,
                    "message": "No subscription found for this user.",
                },
                status=status.HTTP_200_OK,
            )

        serializer = SubscriptionSerializer(subscription)
        history_serializer = SubscriptionSerializer(history, many=True)
        has_active_subscription = subscription.has_active_subscription
        free_remaining = free_usage["remainingFreeUsageCount"]
        can_create_offer, denial_message = resolve_create_offer_access(
            request.user,
            subscription,
            free_remaining,
        )

        message = None if can_create_offer else denial_message

        return Response(
            {
                "hasActiveSubscription": has_active_subscription,
                "activeUsageSource": (
                    "SUBSCRIPTION" if has_active_subscription else "FREE"
                ),
                "canCreateOffer": can_create_offer,
                "subscription": serializer.data,
                "history": history_serializer.data,
                "freeUsage": free_usage,
                "message": message,
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

        try:
            subscription = create_pending_subscription(
                user=request.user,
                plan=plan,
                checkout_session_id=checkout_session.id,
                stripe_customer_id=get_stripe_customer_id(request.user),
            )
        except Exception as e:
            return Response(
                {
                    "detail": (
                        "Checkout started in Stripe but we could not save a "
                        f"pending subscription row: {e}"
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
        subscription = get_current_subscription(request.user)

        if not subscription:
            return Response(
                {"detail": "No subscription found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        stripe_customer_id = get_stripe_customer_id(request.user)
        if not stripe_customer_id and not subscription.stripeCustomerId:
            return Response(
                {"detail": "Stripe customer ID not found for this subscription."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            portal_session = create_customer_portal_session(
                customer_id=stripe_customer_id or subscription.stripeCustomerId,
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


class _SubscriptionActivationResponseMixin:
    def _activation_response(self, request, subscription, *, message):
        subscription.sync_expired_state()
        subscription.refresh_from_db()

        free_usage = MySubscriptionView()._get_free_usage_data(request.user)
        serializer = SubscriptionSerializer(subscription)
        has_active_subscription = subscription.has_active_subscription

        return Response(
            {
                "hasActiveSubscription": has_active_subscription,
                "activeUsageSource": (
                    "SUBSCRIPTION" if has_active_subscription else "FREE"
                ),
                "subscription": serializer.data,
                "freeUsage": free_usage,
                "canUseSubscription": subscription.can_use_subscription,
                "message": message,
            },
            status=status.HTTP_200_OK,
        )


class ConfirmCheckoutSessionView(_SubscriptionActivationResponseMixin, APIView):
    """
    Activate subscription after Stripe Checkout when webhooks cannot reach
    localhost (typical in local development).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = (request.data.get("sessionId") or "").strip() or None

        try:
            subscription = sync_subscription_for_user(
                request.user,
                session_id=session_id,
            )
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not subscription.can_use_subscription:
            return Response(
                {
                    "detail": (
                        "Payment was found but your subscription is not usable yet. "
                        "Please try again in a moment."
                    ),
                    "canUseSubscription": False,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return self._activation_response(
            request,
            subscription,
            message="Subscription activated successfully.",
        )


class SyncSubscriptionView(_SubscriptionActivationResponseMixin, APIView):
    """Pull subscription state from Stripe for the logged-in user."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            subscription = sync_subscription_for_user(request.user)
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if subscription.can_use_subscription:
            return self._activation_response(
                request,
                subscription,
                message="Subscription synced successfully.",
            )

        return self._activation_response(
            request,
            subscription,
            message="Subscription record updated.",
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
            try:
                complete_checkout_session(data_object)
            except Exception as sync_error:
                print("Stripe checkout sync error:", sync_error)

        elif event_type in [
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ]:
            try:
                sync_subscription_from_stripe(data_object)
            except Exception as sync_error:
                print("Stripe subscription sync error:", sync_error)

        elif event_type == "invoice.paid":
            stripe_subscription_id = _stripe_value(data_object, "subscription")
            transaction_id = _stripe_value(data_object, "payment_intent")

            if stripe_subscription_id:
                try:
                    stripe_subscription = stripe.Subscription.retrieve(
                        stripe_subscription_id,
                        expand=["items.data.price"],
                    )

                    sync_subscription_from_stripe(stripe_subscription)

                    if transaction_id:
                        Subscription.objects.filter(
                            stripeSubscriptionId=stripe_subscription_id
                        ).update(
                            transactionId=transaction_id,
                        )

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