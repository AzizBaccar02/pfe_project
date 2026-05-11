from rest_framework import serializers

from cores.models import Localisation
from offers.models import Category, Images, Offre


ALLOWED_TUNISIA_CITIES = [
    "Tunis",
    "Ariana",
    "Ben Arous",
    "Manouba",
    "Nabeul",
    "Zaghouan",
    "Bizerte",
    "Beja",
    "Jendouba",
    "Kef",
    "Siliana",
    "Sousse",
    "Monastir",
    "Mahdia",
    "Sfax",
    "Kairouan",
    "Kasserine",
    "Sidi Bouzid",
    "Gabes",
    "Medenine",
    "Tataouine",
    "Gafsa",
    "Tozeur",
    "Kebili",
]


class OfferImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = Images
        fields = ["id", "url"]
        read_only_fields = ["id", "url"]

    def get_url(self, obj):
        if not obj.url:
            return ""

        request = self.context.get("request")
        url = obj.url.url

        if request is not None:
            return request.build_absolute_uri(url)

        return url


class OfferPublicSerializer(serializers.ModelSerializer):
    images = OfferImageSerializer(many=True, read_only=True)
    category_name = serializers.SerializerMethodField()
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
            "images",
        ]

    def get_category_name(self, obj):
        return obj.category.name if obj.category else ""


class ClientOfferCreateSerializer(serializers.ModelSerializer):
    city = serializers.CharField(write_only=True)
    address = serializers.CharField(write_only=True)
    postalCode = serializers.CharField(write_only=True)

    categoryName = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )

    category_name = serializers.SerializerMethodField()
    country = serializers.CharField(source="localisation.country", read_only=True)
    city_value = serializers.CharField(source="localisation.city", read_only=True)
    address_value = serializers.CharField(source="localisation.address", read_only=True)
    postal_code_value = serializers.CharField(
        source="localisation.postalCode",
        read_only=True,
    )
    images = OfferImageSerializer(many=True, read_only=True)
    interestedAgentsCount = serializers.SerializerMethodField()

    class Meta:
        model = Offre
        fields = [
            "id",
            "title",
            "description",
            "budget",
            "category",
            "categoryName",
            "status",
            "city",
            "address",
            "postalCode",
            "category_name",
            "country",
            "city_value",
            "address_value",
            "postal_code_value",
            "images",
            "interestedAgentsCount",
        ]
        read_only_fields = [
            "id",
            "status",
            "category_name",
            "country",
            "city_value",
            "address_value",
            "postal_code_value",
            "images",
            "interestedAgentsCount",
        ]
        extra_kwargs = {
            "category": {
                "required": False,
                "allow_null": True,
            },
        }

    def get_category_name(self, obj):
        return obj.category.name if obj.category else ""

    def get_interestedAgentsCount(self, obj):
        try:
            from interactions.models import OffreReaction

            return OffreReaction.objects.filter(offre=obj, react=True).count()
        except Exception:
            return 0

    def validate_budget(self, value):
        if value <= 0:
            raise serializers.ValidationError("Budget must be greater than 0.")
        return value

    def validate_city(self, value):
        if value not in ALLOWED_TUNISIA_CITIES:
            raise serializers.ValidationError("Invalid city.")
        return value

    def validate(self, attrs):
        category_name = attrs.get("categoryName", "")
        category = attrs.get("category")

        if not category and not str(category_name).strip():
            raise serializers.ValidationError(
                {"categoryName": "Please select a category."}
            )

        return attrs

    def _resolve_category(self, validated_data):
        category_name = str(validated_data.pop("categoryName", "")).strip()
        category = validated_data.pop("category", None)

        if category_name:
            category, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={"description": ""},
            )
            return category

        return category

    def create(self, validated_data):
        user = self.context["request"].user

        city = validated_data.pop("city")
        address = validated_data.pop("address")
        postal_code = validated_data.pop("postalCode")
        category = self._resolve_category(validated_data)

        localisation = Localisation.objects.create(
            country="Tunisia",
            city=city,
            address=address,
            postalCode=postal_code,
        )

        return Offre.objects.create(
            client=user,
            localisation=localisation,
            category=category,
            **validated_data,
        )


class ClientOfferListSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    country = serializers.CharField(source="localisation.country", read_only=True)
    city = serializers.CharField(source="localisation.city", read_only=True)
    address = serializers.CharField(source="localisation.address", read_only=True)
    postalCode = serializers.CharField(source="localisation.postalCode", read_only=True)
    images = OfferImageSerializer(many=True, read_only=True)
    interestedAgentsCount = serializers.SerializerMethodField()

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
            "images",
            "interestedAgentsCount",
        ]

    def get_category_name(self, obj):
        return obj.category.name if obj.category else ""

    def get_interestedAgentsCount(self, obj):
        try:
            from interactions.models import OffreReaction

            return OffreReaction.objects.filter(offre=obj, react=True).count()
        except Exception:
            return 0


class ClientOfferDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.SerializerMethodField()
    country = serializers.CharField(source="localisation.country", read_only=True)
    city = serializers.CharField(source="localisation.city", read_only=True)
    address = serializers.CharField(source="localisation.address", read_only=True)
    postalCode = serializers.CharField(source="localisation.postalCode", read_only=True)
    images = OfferImageSerializer(many=True, read_only=True)
    interestedAgentsCount = serializers.SerializerMethodField()

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
            "images",
            "interestedAgentsCount",
        ]

    def get_category_name(self, obj):
        return obj.category.name if obj.category else ""

    def get_interestedAgentsCount(self, obj):
        try:
            from interactions.models import OffreReaction

            return OffreReaction.objects.filter(offre=obj, react=True).count()
        except Exception:
            return 0


class ClientOfferUpdateSerializer(serializers.ModelSerializer):
    city = serializers.CharField(write_only=True, required=False)
    address = serializers.CharField(write_only=True, required=False)
    postalCode = serializers.CharField(write_only=True, required=False)

    categoryName = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = Offre
        fields = [
            "title",
            "description",
            "budget",
            "category",
            "categoryName",
            "status",
            "city",
            "address",
            "postalCode",
        ]
        extra_kwargs = {
            "title": {"required": False},
            "description": {"required": False},
            "budget": {"required": False},
            "category": {
                "required": False,
                "allow_null": True,
            },
            "status": {"required": False},
        }

    def validate_budget(self, value):
        if value <= 0:
            raise serializers.ValidationError("Budget must be greater than 0.")
        return value

    def validate_city(self, value):
        if value not in ALLOWED_TUNISIA_CITIES:
            raise serializers.ValidationError("Invalid city.")
        return value

    def update(self, instance, validated_data):
        city = validated_data.pop("city", None)
        address = validated_data.pop("address", None)
        postal_code = validated_data.pop("postalCode", None)

        category_name = str(validated_data.pop("categoryName", "")).strip()

        if category_name:
            category, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={"description": ""},
            )
            instance.category = category
        elif "category" in validated_data:
            instance.category = validated_data.pop("category")

        instance.title = validated_data.get("title", instance.title)
        instance.description = validated_data.get(
            "description",
            instance.description,
        )
        instance.budget = validated_data.get("budget", instance.budget)
        instance.status = validated_data.get("status", instance.status)

        if city is not None or address is not None or postal_code is not None:
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