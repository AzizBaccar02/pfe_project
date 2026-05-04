from rest_framework import serializers

from interactions.models import OffreReaction


class OffreReactionSerializer(serializers.ModelSerializer):
    agent_email = serializers.EmailField(source="agent.email", read_only=True)
    offer_title = serializers.CharField(source="offre.title", read_only=True)

    class Meta:
        model = OffreReaction
        fields = [
            "id",
            "message",
            "proposedPrice",
            "createdAt",
            "status",
            "agent",
            "agent_email",
            "offre",
            "offer_title",
            "react",
        ]
        read_only_fields = [
            "id",
            "createdAt",
            "status",
            "agent",
            "offre",
            "agent_email",
            "offer_title",
        ]