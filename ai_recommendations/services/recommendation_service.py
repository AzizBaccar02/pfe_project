from ai_recommendations.services.embedding_service import (
    cosine_similarity_score,
    generate_embedding,
)


MINIMUM_MATCH_SCORE = 45


def build_agent_text(agent):
    profile = getattr(agent, "profile", None)

    if not profile:
        return ""

    skills = profile.skills or ""
    bio = profile.bio or ""
    hourly_rate = profile.hourlyRate or 0

    localisation = profile.localisation
    city = localisation.city if localisation else ""

    return f"""
    Agent profile:
    Bio: {bio}
    Skills: {skills}
    Hourly rate: {hourly_rate}
    City: {city}
    """


def build_offer_text(offer):
    title = getattr(offer, "title", "") or ""
    description = getattr(offer, "description", "") or ""

    category_name = ""
    if getattr(offer, "category", None):
        category_name = offer.category.name or ""

    localisation = getattr(offer, "localisation", None)
    city = localisation.city if localisation else ""

    return f"""
    Offer:
    Title: {title}
    Description: {description}
    Category: {category_name}
    City: {city}
    """


def get_location_boost(agent, offer):
    agent_profile = getattr(agent, "profile", None)

    if not agent_profile or not agent_profile.localisation:
        return 0

    offer_location = getattr(offer, "localisation", None)

    if not offer_location:
        return 0

    agent_city = agent_profile.localisation.city
    offer_city = offer_location.city

    if not agent_city or not offer_city:
        return 0

    if agent_city.lower() == offer_city.lower():
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

    agent_city_key = agent_city.lower()
    offer_city_key = offer_city.lower()

    if offer_city_key in nearby_cities.get(agent_city_key, []):
        return 5

    return 0


def get_match_level(score):
    if score >= 80:
        return "Excellent match"
    if score >= 65:
        return "Strong match"
    if score >= 45:
        return "Good match"
    return "Not recommended"


def build_ai_reasons(agent, offer, semantic_score, location_boost):
    reasons = []

    if semantic_score >= 65:
        reasons.append(
            "This offer is highly related to your skills and profile description."
        )
    elif semantic_score >= 45:
        reasons.append(
            "This offer has a good semantic match with your agent profile."
        )

    if location_boost == 10:
        reasons.append("This offer is in the same city as your profile.")
    elif location_boost == 5:
        reasons.append("This offer is near your city.")

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

        final_score = round(min(semantic_score + location_boost, 100), 2)

        if final_score < MINIMUM_MATCH_SCORE:
            continue

        recommendations.append(
            {
                "offer": offer,
                "matchScore": final_score,
                "semanticScore": round(semantic_score, 2),
                "locationBoost": location_boost,
                "matchLevel": get_match_level(final_score),
                "aiReasons": build_ai_reasons(
                    agent=agent,
                    offer=offer,
                    semantic_score=semantic_score,
                    location_boost=location_boost,
                ),
            }
        )

    recommendations.sort(
        key=lambda item: item["matchScore"],
        reverse=True,
    )

    return recommendations