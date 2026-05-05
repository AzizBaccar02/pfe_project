from rest_framework import serializers
from offers.models import Offre, Images
from cores.models import Localisation


class ClientOfferCreateSerializer(serializers.ModelSerializer):
    city = serializers.CharField(write_only=True)
    address = serializers.CharField(write_only=True)
    postalCode = serializers.CharField(write_only=True)

    category_name = serializers.CharField(source="category.name", read_only=True)
    country = serializers.CharField(source="localisation.country", read_only=True)
    city_value = serializers.CharField(source="localisation.city", read_only=True)
    address_value = serializers.CharField(source="localisation.address", read_only=True)
    postal_code_value = serializers.CharField(source="localisation.postalCode", read_only=True)

    class Meta:
        model = Offre
        fields = [
            "id",
            "title",
            "description",
            "budget",
            "category",
            "status",
            "city",
            "address",
            "postalCode",
            "category_name",
            "country",
            "city_value",
            "address_value",
            "postal_code_value",
        ]
        read_only_fields = ["id", "status"]

    def validate_budget(self, value):
        if value <= 0:
            raise serializers.ValidationError("Budget must be greater than 0.")
        return value

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

    def create(self, validated_data):
        user = self.context["request"].user

        city = validated_data.pop("city")
        address = validated_data.pop("address")
        postal_code = validated_data.pop("postalCode")

        localisation = Localisation.objects.create(
            country="Tunisia",
            city=city,
            address=address,
            postalCode=postal_code,
        )

        return Offre.objects.create(
            client=user,
            localisation=localisation,
            **validated_data,
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
    city = serializers.CharField(write_only=True, required=False)
    address = serializers.CharField(write_only=True, required=False)
    postalCode = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Offre
        fields = [
            "title",
            "description",
            "budget",
            "category",
            "status",
            "city",
            "address",
            "postalCode",
        ]

    def validate_budget(self, value):
        if value <= 0:
            raise serializers.ValidationError("Budget must be greater than 0.")
        return value

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

        instance.title = validated_data.get("title", instance.title)
        instance.description = validated_data.get("description", instance.description)
        instance.budget = validated_data.get("budget", instance.budget)
        instance.category = validated_data.get("category", instance.category)
        instance.status = validated_data.get("status", instance.status)

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


class OfferImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Images
        fields = ["id", "url"]
        read_only_fields = ["id"]