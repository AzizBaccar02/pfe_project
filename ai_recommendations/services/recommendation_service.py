#recommendations_services.py

from ai_recommendations.services.embedding_service import (
    cosine_similarity_score,
    generate_embedding,
)


MINIMUM_MATCH_SCORE = 45


def safe_value(value, default=""):
    if value is None:
        return default
    return value


def get_profile(user):
    if not user:
        return None

    try:
        return getattr(user, "profile", None)
    except Exception:
        return None


def build_location_text(localisation):
    if not localisation:
        return ""

    city = safe_value(getattr(localisation, "city", ""))
    address = safe_value(getattr(localisation, "address", ""))
    postal_code = safe_value(getattr(localisation, "postalCode", ""))

    return f"""
    City: {city}
    Address: {address}
    Postal code: {postal_code}
    """


def build_agent_text(agent):
    profile = get_profile(agent)

    if not profile:
        return ""

    username = safe_value(getattr(agent, "username", ""))
    role = safe_value(getattr(agent, "role", ""))

    bio = safe_value(getattr(profile, "bio", ""))
    skills = safe_value(getattr(profile, "skills", ""))
    hourly_rate = safe_value(getattr(profile, "hourlyRate", 0))
    rating = safe_value(getattr(profile, "rating", 0))

    localisation_text = build_location_text(getattr(profile, "localisation", None))

    return f"""
    Agent profile:
    Username: {username}
    Role: {role}
    Bio: {bio}
    Skills: {skills}
    Hourly rate: {hourly_rate}
    Rating: {rating}
    Location:
    {localisation_text}
    """


def build_client_text(client):
    if not client:
        return ""

    profile = get_profile(client)

    username = safe_value(getattr(client, "username", ""))
    role = safe_value(getattr(client, "role", ""))

    if not profile:
        return f"""
        Client profile:
        Username: {username}
        Role: {role}
        """

    bio = safe_value(getattr(profile, "bio", ""))
    skills = safe_value(getattr(profile, "skills", ""))
    hourly_rate = safe_value(getattr(profile, "hourlyRate", 0))
    rating = safe_value(getattr(profile, "rating", 0))

    localisation_text = build_location_text(getattr(profile, "localisation", None))

    return f"""
    Client profile:
    Username: {username}
    Role: {role}
    Bio: {bio}
    Skills or activity: {skills}
    Hourly rate: {hourly_rate}
    Rating: {rating}
    Location:
    {localisation_text}
    """


def build_offer_text(offer):
    title = safe_value(getattr(offer, "title", ""))
    description = safe_value(getattr(offer, "description", ""))
    budget = safe_value(getattr(offer, "budget", 0))
    status = safe_value(getattr(offer, "status", ""))

    category_name = ""
    category_description = ""

    category = getattr(offer, "category", None)
    if category:
        category_name = safe_value(getattr(category, "name", ""))
        category_description = safe_value(getattr(category, "description", ""))

    offer_location_text = build_location_text(getattr(offer, "localisation", None))
    client_text = build_client_text(getattr(offer, "client", None))

    return f"""
    Offer:
    Title: {title}
    Description: {description}
    Budget: {budget}
    Status: {status}
    Category name: {category_name}
    Category description: {category_description}
    Offer location:
    {offer_location_text}

    {client_text}
    """


def get_offer_or_client_location(offer):
    offer_location = getattr(offer, "localisation", None)

    if offer_location:
        return offer_location

    client = getattr(offer, "client", None)
    client_profile = get_profile(client)

    if client_profile and client_profile.localisation:
        return client_profile.localisation

    return None


def get_location_boost(agent, offer):
    agent_profile = get_profile(agent)

    if not agent_profile or not agent_profile.localisation:
        return 0

    offer_location = get_offer_or_client_location(offer)

    if not offer_location:
        return 0

    agent_city = safe_value(agent_profile.localisation.city)
    offer_city = safe_value(offer_location.city)

    if not agent_city or not offer_city:
        return 0

    agent_city_key = agent_city.lower().strip()
    offer_city_key = offer_city.lower().strip()

    if agent_city_key == offer_city_key:
        return 10

    nearby_cities = {
        "tunis": ["ariana", "ben arous", "manouba"],
        "ariana": ["tunis", "manouba", "ben arous"],
        "ben arous": ["tunis", "ariana", "manouba"],
        "manouba": ["tunis", "ariana", "ben arous"],
        "sousse": ["monastir", "mahdia", "kairouan"],
        "monastir": ["sousse", "mahdia"],
        "mahdia": ["monastir", "sousse", "sfax"],
        "sfax": ["mahdia", "gabes"],
        "gabes": ["sfax", "medenine"],
        "medenine": ["gabes", "tataouine"],
    }

    if offer_city_key in nearby_cities.get(agent_city_key, []):
        return 5

    return 0


def get_budget_boost(agent, offer):
    agent_profile = get_profile(agent)

    if not agent_profile:
        return 0

    hourly_rate = safe_value(getattr(agent_profile, "hourlyRate", 0), 0)
    budget = safe_value(getattr(offer, "budget", 0), 0)

    try:
        hourly_rate = float(hourly_rate)
        budget = float(budget)
    except Exception:
        return 0

    if hourly_rate <= 0 or budget <= 0:
        return 0

    if budget >= hourly_rate:
        return 5

    return 0


def get_client_rating_boost(offer):
    client = getattr(offer, "client", None)
    client_profile = get_profile(client)

    if not client_profile:
        return 0

    rating = safe_value(getattr(client_profile, "rating", 0), 0)

    try:
        rating = float(rating)
    except Exception:
        return 0

    if rating >= 4.5:
        return 5

    if rating >= 4:
        return 3

    return 0


def get_match_level(score):
    if score >= 80:
        return "Excellent match"
    if score >= 65:
        return "Strong match"
    if score >= 45:
        return "Good match"
    return "Not recommended"


def build_ai_reasons(
    agent,
    offer,
    semantic_score,
    location_boost,
    budget_boost,
    client_rating_boost,
):
    reasons = []

    if semantic_score >= 65:
        reasons.append(
            "This offer strongly matches your full agent profile, including your skills, bio, category context, offer details, and client profile."
        )
    elif semantic_score >= 45:
        reasons.append(
            "This offer has a good match with your agent profile and the client/offer context."
        )

    if location_boost == 10:
        reasons.append("This offer is in the same city as your profile.")
    elif location_boost == 5:
        reasons.append("This offer is near your city.")

    if budget_boost > 0:
        reasons.append("The offer budget is compatible with your hourly rate.")

    if client_rating_boost > 0:
        reasons.append("The client profile has a strong rating.")

    if not reasons:
        reasons.append("This offer has limited similarity with your profile.")

    return reasons


def recommend_offers_for_agent(agent, offers):
    agent_text = build_agent_text(agent)
    agent_embedding = generate_embedding(agent_text)

    recommendations = []

    for offer in offers:
        offer_text = build_offer_text(offer)
        offer_embedding = generate_embedding(offer_text)

        semantic_score = cosine_similarity_score(agent_embedding, offer_embedding) * 100
        location_boost = get_location_boost(agent, offer)
        budget_boost = get_budget_boost(agent, offer)
        client_rating_boost = get_client_rating_boost(offer)

        final_score = round(
            min(
                semantic_score
                + location_boost
                + budget_boost
                + client_rating_boost,
                100,
            ),
            2,
        )

        if final_score < MINIMUM_MATCH_SCORE:
            continue

        recommendations.append(
            {
                "offer": offer,
                "matchScore": final_score,
                "semanticScore": round(semantic_score, 2),
                "locationBoost": location_boost,
                "budgetBoost": budget_boost,
                "clientRatingBoost": client_rating_boost,
                "matchLevel": get_match_level(final_score),
                "aiReasons": build_ai_reasons(
                    agent=agent,
                    offer=offer,
                    semantic_score=semantic_score,
                    location_boost=location_boost,
                    budget_boost=budget_boost,
                    client_rating_boost=client_rating_boost,
                ),
            }
        )

    recommendations.sort(
        key=lambda item: item["matchScore"],
        reverse=True,
    )

    return recommendations