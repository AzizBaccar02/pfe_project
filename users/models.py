from django.db import models
from django.contrib.auth.models import AbstractUser


class Role(models.TextChoices):
    CLIENT = "CLIENT", "CLIENT"
    AGENT = "AGENT", "AGENT"
    ADMIN = "ADMIN", "ADMIN"


class CustomUser(AbstractUser):
    role = models.CharField(max_length=50, choices=Role.choices)
    isEmailVerified = models.BooleanField(default=False)
    isActive = models.BooleanField(default=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    email = models.EmailField(unique=True)


class Profile(models.Model):
    phone = models.CharField(max_length=30)
    photo = models.ImageField(upload_to="profiles/", null=True, blank=True)
    bio = models.TextField()
    skills = models.TextField()
    hourlyRate = models.FloatField()
    rating = models.FloatField()
    user = models.OneToOneField(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="profile"
    )
    localisation = models.ForeignKey(
        "cores.Localisation",
        on_delete=models.SET_NULL,
        null=True,
        related_name="profiles",
    )


class VerificationCode(models.Model):
    code = models.CharField(max_length=20)
    createdAt = models.DateTimeField(auto_now_add=True)
    expiresAt = models.DateTimeField()
    isUsed = models.BooleanField(default=False)
    user = models.OneToOneField(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="verification_code"
    )


class PasswordResetCode(models.Model):
    code = models.CharField(max_length=20)
    createdAt = models.DateTimeField(auto_now_add=True)
    expiresAt = models.DateTimeField()
    isUsed = models.BooleanField(default=False)

    user = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="password_reset_codes",
    )
