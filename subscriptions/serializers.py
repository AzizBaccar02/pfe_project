from rest_framework import serializers

from .models import Plan, Subscription


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = [
            "id",
            "name",
            "description",
            "price",
            "period",
            "features",
            "usageLimit",
            "isActive",
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = PlanSerializer(read_only=True)
    hasActiveSubscription = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            "id",
            "plan",
            "status",
            "startDate",
            "endDate",
            "isActive",
            "cancelAtPeriodEnd",
            "hasActiveSubscription",
            "createdAt",
            "updatedAt",
            "usageLimit",
            "remainingUsageCount",
            "usedUsageCount",
        ]

    def get_hasActiveSubscription(self, obj):
        return obj.has_active_subscription