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

        profile = getattr(request.user, "profile", None)

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
            .select_related("category", "localisation", "client")
            .order_by("-createdAt")
        )

        recommendations = recommend_offers_for_agent(
            agent=request.user,
            offers=offers,
        )

        limit = request.query_params.get("limit", 20)

        try:
            limit = int(limit)
        except ValueError:
            limit = 20

        recommendations = recommendations[:limit]

        data = []

        for item in recommendations:
            offer = item["offer"]

            localisation = offer.localisation
            category = offer.category
            client = offer.client

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
                    "createdAt": offer.createdAt,
                    "matchScore": item["matchScore"],
                    "semanticScore": item["semanticScore"],
                    "locationBoost": item["locationBoost"],
                    "matchLevel": item["matchLevel"],
                    "aiReasons": item["aiReasons"],
                }
            )

        serializer = RecommendedOfferSerializer(data, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)