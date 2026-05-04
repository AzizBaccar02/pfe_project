import stripe

from django.conf import settings


stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(*, user, plan):
    if not settings.STRIPE_SECRET_KEY:
        raise ValueError("Stripe secret key is not configured.")

    if not plan.stripePriceId:
        raise ValueError("This plan does not have a Stripe price ID.")

    checkout_session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=user.email,
        line_items=[
            {
                "price": plan.stripePriceId,
                "quantity": 1,
            }
        ],
        success_url=settings.STRIPE_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=settings.STRIPE_CANCEL_URL,
        metadata={
            "user_id": str(user.id),
            "plan_id": str(plan.id),
        },
        subscription_data={
            "metadata": {
                "user_id": str(user.id),
                "plan_id": str(plan.id),
            }
        },
    )

    return checkout_session


def create_customer_portal_session(*, customer_id):
    if not settings.STRIPE_SECRET_KEY:
        raise ValueError("Stripe secret key is not configured.")

    if not customer_id:
        raise ValueError("Stripe customer ID is required.")

    portal_session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=settings.STRIPE_PORTAL_RETURN_URL,
    )

    return portal_session