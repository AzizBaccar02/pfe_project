from django.db import models


class OffreStatut(models.TextChoices):
    OPEN = 'OPEN', 'OPEN'
    CLOSED = 'CLOSED', 'CLOSED'
    ARCHIVED = 'ARCHIVED', 'ARCHIVED'


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()


class Offre(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    budget = models.FloatField()
    createdAt = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=OffreStatut.choices, default=OffreStatut.OPEN)
    localisation = models.ForeignKey(
        "cores.Localisation",
        on_delete=models.SET_NULL,
        null=True,
        related_name="offres"
    )
    client = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="client_offres"
    )
    category = models.ForeignKey(
        "offers.Category",
        on_delete=models.SET_NULL,
        null=True,
        related_name="category_offres"
    )
