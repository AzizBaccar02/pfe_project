from django.db import models


class DemandeStatus(models.TextChoices):
    PENDING = 'PENDING', 'PENDING'
    ACCEPTED = 'ACCEPTED', 'ACCEPTED'
    REJECTED = 'REJECTED', 'REJECTED'


class OffreReaction(models.Model):
    message = models.TextField()
    proposedPrice = models.FloatField()
    createdAt = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=DemandeStatus.choices, )
    agent = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="agent_reactions"
    )
    offre = models.ForeignKey(
        "offers.Offre",
        on_delete=models.CASCADE,
        related_name="reactions"
    )
    react = models.BooleanField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["agent", "offre"], name="unique_agent_offre_reaction"),
        ]
