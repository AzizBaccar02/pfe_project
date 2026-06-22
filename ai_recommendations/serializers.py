#C:\Users\Lenovo\django_project\pfe_project2\pfe_project\ai_recommendations\serializers.py

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
    clientRating = serializers.FloatField(required=False)
    clientCity = serializers.CharField(required=False, allow_blank=True)
    createdAt = serializers.DateTimeField()

    matchScore = serializers.FloatField()
    skillsScore = serializers.FloatField()
    semanticScore = serializers.FloatField()
    keywordSkillsScore = serializers.FloatField(required=False)
    locationBoost = serializers.IntegerField()
    locationTier = serializers.IntegerField()
    locationLabel = serializers.CharField()
    budgetBoost = serializers.IntegerField()
    clientRatingBoost = serializers.IntegerField()
    matchLevel = serializers.CharField()
    aiReasons = serializers.ListField(child=serializers.CharField())