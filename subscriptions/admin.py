from django.contrib import admin

from .models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "price",
        "period",
        "usageLimit",
        "isActive",
        "stripePriceId",
        "createdAt",
    )
    list_filter = ("period", "isActive", "createdAt")
    search_fields = ("name", "stripeProductId", "stripePriceId")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "plan",
        "status",
        "isActive",
        "startDate",
        "endDate",
        "createdAt",
        "usageLimit",
        "remainingUsageCount",
        "usedUsageCount",
    )
    list_filter = ("status", "isActive", "createdAt")
    search_fields = (
        "user__email",
        "stripeCustomerId",
        "stripeSubscriptionId",
        "stripeCheckoutSessionId",
        "transactionId",
    )