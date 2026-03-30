from rest_framework import serializers
from offers.models import Offre, Images

class OfferImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Images
        fields = ["id", "url"]

class OfferPublicSerializer(serializers.ModelSerializer):
    images = OfferImageSerializer(many=True, read_only=True)

    class Meta:
        model = Offre
        fields = ["id", "title", "description", "budget", "status", "createdAt", "category", "localisation", "images"]