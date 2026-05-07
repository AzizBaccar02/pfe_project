from django.db import transaction

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import Role
from offers.models import Offre, Images, OffreStatut
from subscriptions.services.usage_service import (
    SubscriptionUsageAction,
    consume_subscription_usage,
)

from .serializers import (
    ClientOfferCreateSerializer,
    ClientOfferDetailSerializer,
    ClientOfferListSerializer,
    ClientOfferUpdateSerializer,
    OfferImageSerializer,
)


class ClientOfferListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can access their offers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        offers = (
            Offre.objects.filter(client=request.user)
            .select_related("localisation", "category")
            .prefetch_related("images")
            .order_by("-createdAt")
        )

        serializer = ClientOfferListSerializer(
            offers,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can create offers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ClientOfferCreateSerializer(
            data=request.data,
            context={"request": request},
        )

        if serializer.is_valid():
            with transaction.atomic():
                consume_subscription_usage(
                    request.user,
                    SubscriptionUsageAction.CREATE_OFFER,
                )

                offer = serializer.save()

            detail_serializer = ClientOfferDetailSerializer(
                offer,
                context={"request": request},
            )
            return Response(
                detail_serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClientOfferDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, offer_id):
        try:
            return (
                Offre.objects.select_related("localisation", "category")
                .prefetch_related("images")
                .get(id=offer_id, client=request.user)
            )
        except Offre.DoesNotExist:
            return None

    def get(self, request, offer_id):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can access offer details."},
                status=status.HTTP_403_FORBIDDEN,
            )

        offer = self.get_object(request, offer_id)
        if not offer:
            return Response(
                {"detail": "Offer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ClientOfferDetailSerializer(
            offer,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, offer_id):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can update offers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        offer = self.get_object(request, offer_id)
        if not offer:
            return Response(
                {"detail": "Offer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ClientOfferUpdateSerializer(
            offer,
            data=request.data,
            context={"request": request},
        )

        if serializer.is_valid():
            updated_offer = serializer.save()

            detail_serializer = ClientOfferDetailSerializer(
                updated_offer,
                context={"request": request},
            )
            return Response(detail_serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, offer_id):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can update offers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        offer = self.get_object(request, offer_id)
        if not offer:
            return Response(
                {"detail": "Offer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ClientOfferUpdateSerializer(
            offer,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        if serializer.is_valid():
            updated_offer = serializer.save()

            detail_serializer = ClientOfferDetailSerializer(
                updated_offer,
                context={"request": request},
            )
            return Response(detail_serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, offer_id):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can delete offers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        offer = self.get_object(request, offer_id)
        if not offer:
            return Response(
                {"detail": "Offer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        offer.delete()
        return Response(
            {"detail": "Offer deleted successfully."},
            status=status.HTTP_204_NO_CONTENT,
        )


class ClientOfferImagesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, offer_id):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can upload offer images."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            offer = Offre.objects.get(id=offer_id, client=request.user)
        except Offre.DoesNotExist:
            return Response(
                {"detail": "Offer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        files = request.FILES.getlist("images")
        if not files:
            return Response(
                {"detail": "No images provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_images = []

        for file in files:
            image = Images.objects.create(offre=offer, url=file)
            created_images.append(image)

        serializer = OfferImageSerializer(
            created_images,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request, offer_id):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can view offer images."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            offer = Offre.objects.get(id=offer_id, client=request.user)
        except Offre.DoesNotExist:
            return Response(
                {"detail": "Offer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = OfferImageSerializer(
            offer.images.all(),
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class ClientOfferStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, offer_id):
        if request.user.role != Role.CLIENT:
            return Response(
                {"detail": "Only clients can change offer status."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            offer = (
                Offre.objects.select_related("localisation", "category")
                .prefetch_related("images")
                .get(id=offer_id, client=request.user)
            )
        except Offre.DoesNotExist:
            return Response(
                {"detail": "Offer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        new_status = request.data.get("status")
        allowed_statuses = [
            OffreStatut.OPEN,
            OffreStatut.CLOSED,
            OffreStatut.ARCHIVED,
        ]

        if new_status not in allowed_statuses:
            return Response(
                {"detail": "Invalid status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        offer.status = new_status
        offer.save()

        serializer = ClientOfferDetailSerializer(
            offer,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)