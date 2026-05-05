from rest_framework import serializers


class RecommendedOfferSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    description = serializers.CharField()
    budget = serializers.FloatField()
    status = serializers.CharField()
    category = serializers.CharField(allow_blank=True)
    city = serializers.CharField(allow_blank=True)
    address = serializers.CharField(allow_blank=True)
    postalCode = serializers.CharField(allow_blank=True)
    clientId = serializers.IntegerField()
    clientUsername = serializers.CharField(allow_blank=True)
    createdAt = serializers.DateTimeField()

    matchScore = serializers.FloatField()
    semanticScore = serializers.FloatField()
    locationBoost = serializers.IntegerField()
    matchLevel = serializers.CharField()
    aiReasons = serializers.ListField(child=serializers.CharField())