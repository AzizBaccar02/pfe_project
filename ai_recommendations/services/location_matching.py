import re
import unicodedata

# Tunisian governorates / main cities (longest names first for substring matching).
TUNISIA_CITIES = [
    "ben arous",
    "la marsa",
    "la goulette",
    "la soukra",
    "tataouine",
    "kairouan",
    "monastir",
    "mahdia",
    "medenine",
    "zaghouan",
    "jendouba",
    "bizerte",
    "manouba",
    "nabeul",
    "siliana",
    "gabes",
    "sfax",
    "beja",
    "ariana",
    "gafsa",
    "kebili",
    "sousse",
    "tozeur",
    "tunis",
    "kef",
]

# Nearby map uses canonical city keys only.
NEARBY_CITIES = {
    "tunis": ["ariana", "ben arous", "manouba", "la marsa", "la goulette"],
    "ariana": ["tunis", "manouba", "ben arous", "la soukra"],
    "la soukra": ["ariana", "tunis", "ben arous", "manouba"],
    "ben arous": ["tunis", "ariana", "manouba"],
    "manouba": ["tunis", "ariana", "ben arous"],
    "sousse": ["monastir", "mahdia", "kairouan"],
    "monastir": ["sousse", "mahdia"],
    "mahdia": ["monastir", "sousse", "sfax"],
    "sfax": ["mahdia", "gabes"],
    "gabes": ["sfax", "medenine"],
    "medenine": ["gabes", "tataouine"],
}

# La Soukra is part of Ariana governorate.
CITY_ALIASES = {
    "la soukra": "ariana",
    "soukra": "ariana",
    "cite el ghazala": "ariana",
    "raoued": "ariana",
    "mnihla": "ariana",
    "kalaat el andalous": "nabeul",
    "hammam lif": "ben arous",
    "hammam chatt": "ben arous",
    "borj el amri": "manouba",
    "djedeida": "manouba",
    "la marsa": "tunis",
    "la goulette": "tunis",
    "carthage": "tunis",
}


def _strip_accents(value):
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _clean_text(value):
    if not value:
        return ""

    text = _strip_accents(str(value).lower().strip())
    text = text.replace("'", " ").replace("-", " ")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_city_key(*parts):
    """
    Extract a canonical Tunisia city key from city/address text.
    Examples:
      "Ariana La Soukra" -> "ariana"
      "La Soukra" -> "ariana"
      "Ariana" -> "ariana"
    """
    combined = _clean_text(" ".join(part for part in parts if part))
    if not combined:
        return ""

    for city in sorted(TUNISIA_CITIES, key=len, reverse=True):
        if city in combined:
            return CITY_ALIASES.get(city, city)

    return ""


def resolve_location_keys(localisation):
    if not localisation:
        return ""

    city = getattr(localisation, "city", "") or ""
    address = getattr(localisation, "address", "") or ""
    postal_code = getattr(localisation, "postalCode", "") or ""

    return normalize_city_key(city, address, postal_code)


def cities_are_same(agent_key, offer_key):
    return bool(agent_key and offer_key and agent_key == offer_key)


def cities_are_nearby(agent_key, offer_key):
    if not agent_key or not offer_key or agent_key == offer_key:
        return False

    nearby = NEARBY_CITIES.get(agent_key, [])
    return offer_key in nearby
