from django.conf import settings
from django.db import models
from django.utils import timezone


class PlanPeriod(models.TextChoices):
    MONTHLY = "MONTHLY", "Monthly"
    YEARLY = "YEARLY", "Yearly"


class PlanTargetRole(models.TextChoices):
    CLIENT = "CLIENT", "Client"
    AGENT = "AGENT", "Agent"


class PlanType(models.TextChoices):
    USAGE = "USAGE", "Usage based"
    DATE = "DATE", "Date based"


class SubscriptionStatus(models.TextChoices):
    INCOMPLETE = "INCOMPLETE", "Incomplete"
    ACTIVE = "ACTIVE", "Active"
    PAST_DUE = "PAST_DUE", "Past due"
    CANCELED = "CANCELED", "Canceled"
    UNPAID = "UNPAID", "Unpaid"
    EXPIRED = "EXPIRED", "Expired"


class Plan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    targetRole = models.CharField(
        max_length=20,
        choices=PlanTargetRole.choices,
        default=PlanTargetRole.CLIENT,
    )

    planType = models.CharField(
        max_length=20,
        choices=PlanType.choices,
        default=PlanType.USAGE,
    )

    period = models.CharField(
        max_length=20,
        choices=PlanPeriod.choices,
        default=PlanPeriod.MONTHLY,
    )

    features = models.JSONField(default=list, blank=True)

    # For USAGE plans:
    # Client plan = number of offers
    # Agent plan = number of reactions
    usageLimit = models.PositiveIntegerField(default=100)

    # Stripe fields
    stripeProductId = models.CharField(max_length=255, blank=True, null=True)
    stripePriceId = models.CharField(max_length=255, unique=True)

    isActive = models.BooleanField(default=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.targetRole} - {self.planType}"


class Subscription(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription",
    )

    plan = models.ForeignKey(
        Plan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subscriptions",
    )

    status = models.CharField(
        max_length=30,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.INCOMPLETE,
    )

    startDate = models.DateTimeField(null=True, blank=True)
    endDate = models.DateTimeField(null=True, blank=True)
    isActive = models.BooleanField(default=False)

    usageLimit = models.PositiveIntegerField(default=0)
    remainingUsageCount = models.PositiveIntegerField(default=0)
    usedUsageCount = models.PositiveIntegerField(default=0)

    # Stripe fields
    stripeCustomerId = models.CharField(max_length=255, blank=True, null=True)
    stripeSubscriptionId = models.CharField(max_length=255, blank=True, null=True)
    stripeCheckoutSessionId = models.CharField(max_length=255, blank=True, null=True)

    transactionId = models.CharField(max_length=255, blank=True, null=True)

    cancelAtPeriodEnd = models.BooleanField(default=False)

    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - {self.status}"

    @property
    def has_active_subscription(self):
        if self.status != SubscriptionStatus.ACTIVE or not self.isActive:
            return False

        if self.plan and self.plan.planType == PlanType.DATE:
            if self.endDate and timezone.now() > self.endDate:
                return False

        return True

    @property
    def can_use_subscription(self):
        if not self.has_active_subscription:
            return False

        if self.plan and self.plan.planType == PlanType.DATE:
            return True

        return self.remainingUsageCount > 0