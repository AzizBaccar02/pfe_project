from rest_framework import serializers
from offers.models import Offre, Images


class ClientOfferCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offre
        fields = ["id", "title", "description", "budget", "category", "localisation", "status"]
        read_only_fields = ["id", "status"]

    def create(self, validated_data):
        user = self.context["request"].user
        return Offre.objects.create(
            client=user,
            **validated_data
        )


class ClientOfferListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    city = serializers.CharField(source="localisation.city", read_only=True)

    class Meta:
        model = Offre
        fields = [
            "id",
            "title",
            "description",
            "budget",
            "status",
            "createdAt",
            "category",
            "category_name",
            "localisation",
            "city",
        ]


class ClientOfferDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    country = serializers.CharField(source="localisation.country", read_only=True)
    city = serializers.CharField(source="localisation.city", read_only=True)
    address = serializers.CharField(source="localisation.address", read_only=True)
    postalCode = serializers.CharField(source="localisation.postalCode", read_only=True)

    class Meta:
        model = Offre
        fields = [
            "id",
            "title",
            "description",
            "budget",
            "status",
            "createdAt",
            "category",
            "category_name",
            "localisation",
            "country",
            "city",
            "address",
            "postalCode",
        ]


class ClientOfferUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Offre
        fields = ["title", "description", "budget", "category", "localisation", "status"]


class OfferImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Images
        fields = ["id", "url"]
        read_only_fields = ["id"]