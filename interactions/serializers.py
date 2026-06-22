#interactions\serializers.py

from rest_framework import serializers

from interactions.models import OffreReaction, OfferReactionStatus


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


class ClientInterestedAgentSerializer(serializers.ModelSerializer):
    reactionId = serializers.IntegerField(source="id", read_only=True)
    id = serializers.IntegerField(source="agent.id", read_only=True)

    name = serializers.SerializerMethodField()
    jobTitle = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    completedJobs = serializers.SerializerMethodField()
    imageUrl = serializers.SerializerMethodField()

    offerId = serializers.IntegerField(source="offre.id", read_only=True)
    offerTitle = serializers.CharField(source="offre.title", read_only=True)

    proposedPrice = serializers.SerializerMethodField()

    class Meta:
        model = OffreReaction
        fields = [
            "reactionId",
            "id",
            "name",
            "jobTitle",
            "city",
            "rating",
            "completedJobs",
            "imageUrl",
            "offerId",
            "offerTitle",
            "message",
            "proposedPrice",
            "status",
            "createdAt",
        ]

    def _get_profile(self, obj):
        try:
            return obj.agent.profile
        except Exception:
            return None

    def get_name(self, obj):
        first_name = (obj.agent.first_name or "").strip()
        last_name = (obj.agent.last_name or "").strip()

        full_name = f"{first_name} {last_name}".strip()

        if full_name:
            return full_name

        if obj.agent.username:
            return obj.agent.username

        return obj.agent.email

    def get_jobTitle(self, obj):
        profile = self._get_profile(obj)

        if profile and profile.skills:
            first_skill = str(profile.skills).split(",")[0].strip()
            if first_skill:
                return first_skill

        if profile and profile.bio:
            return "Service Agent"

        return "Agent"

    def get_city(self, obj):
        profile = self._get_profile(obj)

        if profile and profile.localisation:
            return profile.localisation.city or ""

        return ""

    def get_rating(self, obj):
        profile = self._get_profile(obj)

        if profile and profile.rating is not None:
            return float(profile.rating)

        return 0.0

    def get_completedJobs(self, obj):
        return OffreReaction.objects.filter(
            agent=obj.agent,
            status=OfferReactionStatus.ACCEPTED,
        ).count()

    def get_imageUrl(self, obj):
        profile = self._get_profile(obj)

        if not profile or not profile.photo:
            return ""

        try:
            url = profile.photo.url
        except Exception:
            return ""

        request = self.context.get("request")

        if request is not None:
            return request.build_absolute_uri(url)

        return url

    def get_proposedPrice(self, obj):
        if obj.proposedPrice is None:
            return ""

        return str(obj.proposedPrice)