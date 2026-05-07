from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from offers.models import Offre, OffreStatut
from users.models import Role
from ai_recommendations.serializers import RecommendedOfferSerializer
from ai_recommendations.services.recommendation_service import (
    recommend_offers_for_agent,
)


class AgentRecommendedOffersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != Role.AGENT:
            return Response(
                {"detail": "Only agents can access AI recommended offers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        agent = request.user
        profile = getattr(agent, "profile", None)

        if not profile:
            return Response(
                {"detail": "Agent profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not profile.skills and not profile.bio:
            return Response(
                {
                    "detail": "Please complete your profile skills or bio to get AI recommendations."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        offers = (
            Offre.objects
            .filter(status=OffreStatut.OPEN)
            .exclude(reactions__agent=agent)
            .select_related(
                "category",
                "localisation",
                "client",
                "client__profile",
                "client__profile__localisation",
            )
            .order_by("-createdAt")
            .distinct()
        )

        recommendations = recommend_offers_for_agent(
            agent=agent,
            offers=offers,
        )

        limit = request.query_params.get("limit", 20)

        try:
            limit = int(limit)
        except ValueError:
            limit = 20

        if limit <= 0:
            limit = 20

        if limit > 100:
            limit = 100

        recommendations = recommendations[:limit]

        data = []

        for item in recommendations:
            offer = item["offer"]

            localisation = offer.localisation
            category = offer.category
            client = offer.client

            try:
                client_profile = client.profile if client else None
            except Exception:
                client_profile = None

            client_location = client_profile.localisation if client_profile else None

            data.append(
                {
                    "id": offer.id,
                    "title": offer.title,
                    "description": offer.description,
                    "budget": offer.budget,
                    "status": offer.status,
                    "category": category.name if category else "",
                    "city": localisation.city if localisation else "",
                    "address": localisation.address if localisation else "",
                    "postalCode": localisation.postalCode if localisation else "",
                    "clientId": client.id if client else 0,
                    "clientUsername": client.username if client else "",
                    "clientRating": client_profile.rating if client_profile else 0,
                    "clientCity": client_location.city if client_location else "",
                    "createdAt": offer.createdAt,
                    "matchScore": item["matchScore"],
                    "semanticScore": item["semanticScore"],
                    "locationBoost": item["locationBoost"],
                    "budgetBoost": item["budgetBoost"],
                    "clientRatingBoost": item["clientRatingBoost"],
                    "matchLevel": item["matchLevel"],
                    "aiReasons": item["aiReasons"],
                }
            )

        serializer = RecommendedOfferSerializer(data, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)