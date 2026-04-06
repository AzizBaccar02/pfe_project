from rest_framework import serializers
from users.models import Profile
from cores.models import Localisation


class AgentProfileSerializer(serializers.ModelSerializer):
    city = serializers.CharField(write_only=True, required=False)
    address = serializers.CharField(write_only=True, required=False)
    postalCode = serializers.CharField(write_only=True, required=False)

    country = serializers.CharField(source="localisation.country", read_only=True)
    city_value = serializers.CharField(source="localisation.city", read_only=True)
    address_value = serializers.CharField(source="localisation.address", read_only=True)
    postal_code_value = serializers.CharField(source="localisation.postalCode", read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "phone",
            "photo",
            "bio",
            "skills",
            "hourlyRate",
            "rating",
            "city",
            "address",
            "postalCode",
            "country",
            "city_value",
            "address_value",
            "postal_code_value",
        ]
        read_only_fields = ["id", "rating"]

    def validate_city(self, value):
        allowed_cities = [
            "Tunis", "Ariana", "Ben Arous", "Manouba", "Nabeul", "Zaghouan",
            "Bizerte", "Beja", "Jendouba", "Kef", "Siliana", "Sousse",
            "Monastir", "Mahdia", "Sfax", "Kairouan", "Kasserine",
            "Sidi Bouzid", "Gabes", "Medenine", "Tataouine",
            "Gafsa", "Tozeur", "Kebili",
        ]
        if value not in allowed_cities:
            raise serializers.ValidationError("Invalid city.")
        return value

    def update(self, instance, validated_data):
        city = validated_data.pop("city", None)
        address = validated_data.pop("address", None)
        postal_code = validated_data.pop("postalCode", None)

        instance.phone = validated_data.get("phone", instance.phone)
        instance.photo = validated_data.get("photo", instance.photo)
        instance.bio = validated_data.get("bio", instance.bio)
        instance.skills = validated_data.get("skills", instance.skills)
        instance.hourlyRate = validated_data.get("hourlyRate", instance.hourlyRate)

        if city or address or postal_code:
            if instance.localisation:
                instance.localisation.country = "Tunisia"
                if city is not None:
                    instance.localisation.city = city
                if address is not None:
                    instance.localisation.address = address
                if postal_code is not None:
                    instance.localisation.postalCode = postal_code
                instance.localisation.save()
            else:
                instance.localisation = Localisation.objects.create(
                    country="Tunisia",
                    city=city or "",
                    address=address or "",
                    postalCode=postal_code or "",
                )

        instance.save()
        return instance