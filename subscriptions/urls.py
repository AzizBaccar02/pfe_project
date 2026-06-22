#subscriptions\urls.py

from django.urls import path

from .views import (
    ConfirmCheckoutSessionView,
    CreateCheckoutSessionView,
    CreateCustomerPortalSessionView,
    MySubscriptionView,
    PlanListView,
    SyncSubscriptionView,
    stripe_webhook_view,
    subscription_cancel_view,
    subscription_success_view,
)

urlpatterns = [
    path("plans/", PlanListView.as_view(), name="subscription-plans"),
    path("me/", MySubscriptionView.as_view(), name="my-subscription"),
    path(
        "create-checkout-session/",
        CreateCheckoutSessionView.as_view(),
        name="create-checkout-session",
    ),
    path(
        "create-portal-session/",
        CreateCustomerPortalSessionView.as_view(),
        name="create-portal-session",
    ),
    path(
        "confirm-checkout-session/",
        ConfirmCheckoutSessionView.as_view(),
        name="confirm-checkout-session",
    ),
    path(
        "sync/",
        SyncSubscriptionView.as_view(),
        name="sync-subscription",
    ),
    path("success/", subscription_success_view, name="subscription-success"),
    path("cancel/", subscription_cancel_view, name="subscription-cancel"),
    path("webhook/", stripe_webhook_view, name="stripe-webhook"),
]