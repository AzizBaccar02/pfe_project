#C:\Users\Lenovo\django_project\pfe_project2\pfe_project\ai_recommendations\services\recommendation_service.py

from ai_recommendations.services.embedding_service import (
    EmbeddingTimeoutError,
    cosine_similarity_score,
    generate_embedding,
    generate_embeddings_batch,
)
from ai_recommendations.services.skills_matching import (
    build_agent_skills_text,
    build_offer_skills_text,
    build_skills_reasons,
    combine_skills_score,
    compute_keyword_skills_score,
    get_agent_skill_tokens,
    get_matched_skill_tokens,
    get_offer_category_name,
    get_offer_search_corpus,
    passes_skills_filter,
)
from ai_recommendations.services.location_matching import (
    cities_are_nearby,
    cities_are_same,
    normalize_city_key,
    resolve_location_keys,
)


MINIMUM_MATCH_SCORE = 45

# NLP runs only on this many offers after location pre-filter (keeps response fast).
MAX_NLP_CANDIDATES = 12
MIN_KEYWORD_FOR_FAR_OFFERS = 1

LOCATION_TIER_SAME_CITY = 3
LOCATION_TIER_NEARBY = 2
LOCATION_TIER_OTHER = 1
LOCATION_TIER_UNKNOWN = 0

SORT_LOCATION_SKILLS = "location_skills"
SORT_MATCH_SCORE = "score"

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

    agent_city_key = resolve_location_keys(agent_profile.localisation)
    offer_city_key = resolve_location_keys(offer_location)

    if not agent_city_key or not offer_city_key:
        return 0

    if cities_are_same(agent_city_key, offer_city_key):
        return 10

    if cities_are_nearby(agent_city_key, offer_city_key):
        return 5

    return 0


def get_agent_city(agent):
    agent_profile = get_profile(agent)

    if not agent_profile or not agent_profile.localisation:
        return ""

    raw_city = safe_value(agent_profile.localisation.city).strip()
    canonical = resolve_location_keys(agent_profile.localisation)

    if raw_city and canonical:
        return raw_city if canonical in raw_city.lower() else raw_city

    if canonical:
        return canonical.title()

    return raw_city


def get_location_tier_and_label(agent, offer):
    location_boost = get_location_boost(agent, offer)
    offer_location = get_offer_or_client_location(offer)
    offer_city = (
        safe_value(getattr(offer_location, "city", "")).strip()
        if offer_location
        else ""
    )
    agent_city = get_agent_city(agent)

    if location_boost == 10:
        if offer_city:
            label = f"Same area · {offer_city}"
        else:
            label = "Same area as you"
        return LOCATION_TIER_SAME_CITY, label

    if location_boost == 5:
        label = f"Nearby · {offer_city}" if offer_city else "Near your area"
        return LOCATION_TIER_NEARBY, label

    if offer_city:
        if agent_city:
            return LOCATION_TIER_OTHER, f"{offer_city} · farther from {agent_city}"
        return LOCATION_TIER_OTHER, offer_city

    return LOCATION_TIER_UNKNOWN, "Location not specified"


def sort_recommendations(recommendations, sort_mode=SORT_LOCATION_SKILLS):
    if sort_mode == SORT_MATCH_SCORE:
        recommendations.sort(
            key=lambda item: (item["matchScore"], item["skillsScore"]),
            reverse=True,
        )
        return recommendations

    recommendations.sort(
        key=lambda item: (
            -item["locationTier"],
            -item["skillsScore"],
            -item["matchScore"],
        ),
    )

    return recommendations


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
    skills_score,
    skills_reasons,
    location_boost,
    budget_boost,
    client_rating_boost,
):
    reasons = list(skills_reasons)

    if location_boost == 10:
        reasons.append("This offer is in the same city as your profile.")
    elif location_boost == 5:
        reasons.append("This offer is near your city.")

    if budget_boost > 0:
        reasons.append("The offer budget is compatible with your hourly rate.")

    if client_rating_boost > 0:
        reasons.append("The client profile has a strong rating.")

    if not reasons:
        if skills_score >= 45:
            reasons.append("This offer matches your profile skills and location.")
        else:
            reasons.append("This offer has limited similarity with your profile.")

    return reasons


def _pre_rank_offers_by_location(agent, offer_list):
    """
    Phase 1 (fast): location tier + keyword skills only — no NLP.
    Returns items sorted by nearest location first, then keyword overlap.
    """
    agent_skill_tokens = get_agent_skill_tokens(agent)
    pre_ranked = []

    for offer in offer_list:
        location_boost = get_location_boost(agent, offer)
        location_tier, location_label = get_location_tier_and_label(agent, offer)
        category_name = get_offer_category_name(offer)
        offer_corpus = get_offer_search_corpus(offer)
        keyword_score = compute_keyword_skills_score(
            agent_skill_tokens,
            offer_corpus,
            category_name=category_name,
        )
        matched_tokens = get_matched_skill_tokens(
            agent_skill_tokens,
            offer_corpus,
            category_name=category_name,
        )

        pre_ranked.append(
            {
                "offer": offer,
                "location_boost": location_boost,
                "location_tier": location_tier,
                "location_label": location_label,
                "keyword_score": keyword_score,
                "offer_corpus": offer_corpus,
                "category_name": category_name,
                "has_skill_match": len(matched_tokens) > 0,
            }
        )

    pre_ranked.sort(
        key=lambda item: (
            -item["location_tier"],
            -item["keyword_score"],
        ),
    )

    return pre_ranked, agent_skill_tokens


def _select_nlp_candidates(pre_ranked, max_candidates=MAX_NLP_CANDIDATES):
    """
    Pick offers that will go through NLP — local offers first, far offers only
  if they already have a keyword skills hint.
    """
    candidates = []

    for item in pre_ranked:
        if len(candidates) >= max_candidates:
            break

        tier = item["location_tier"]
        keyword_score = item["keyword_score"]
        has_skill_match = item["has_skill_match"]

        if tier >= LOCATION_TIER_NEARBY:
            candidates.append(item)
            continue

        if has_skill_match and keyword_score >= MIN_KEYWORD_FOR_FAR_OFFERS:
            candidates.append(item)
            continue

    return candidates


def _append_recommendation(
    recommendations,
    agent,
    offer,
    item,
    agent_skill_tokens,
    skills_score,
    embedding_score,
    keyword_score,
):
    location_boost = item["location_boost"]
    location_tier = item["location_tier"]
    location_label = item["location_label"]
    offer_corpus = item["offer_corpus"]
    category_name = item.get("category_name", "")

    budget_boost = get_budget_boost(agent, offer)
    client_rating_boost = get_client_rating_boost(offer)

    final_score = round(
        min(
            skills_score
            + location_boost
            + budget_boost
            + client_rating_boost,
            100,
        ),
        2,
    )

    has_skill_match = item.get("has_skill_match", False)

    if not passes_skills_filter(
        skills_score,
        location_tier,
        keyword_score,
        has_skill_match,
    ):
        return

    if final_score < MINIMUM_MATCH_SCORE and location_tier < LOCATION_TIER_SAME_CITY:
        if not (has_skill_match and keyword_score >= 40):
            return

    skills_reasons = build_skills_reasons(
        agent_skill_tokens,
        offer_corpus,
        skills_score,
        category_name=category_name,
    )

    recommendations.append(
        {
            "offer": offer,
            "matchScore": final_score,
            "skillsScore": skills_score,
            "semanticScore": round(embedding_score, 2),
            "keywordSkillsScore": keyword_score,
            "locationBoost": location_boost,
            "locationTier": location_tier,
            "locationLabel": location_label,
            "budgetBoost": budget_boost,
            "clientRatingBoost": client_rating_boost,
            "matchLevel": get_match_level(final_score),
            "aiReasons": build_ai_reasons(
                agent=agent,
                offer=offer,
                skills_score=skills_score,
                skills_reasons=skills_reasons,
                location_boost=location_boost,
                budget_boost=budget_boost,
                client_rating_boost=client_rating_boost,
            ),
        }
    )


def _build_keyword_only_recommendations(agent, pre_ranked, agent_skill_tokens):
    """Fallback when NLP filters everything out — keep clear skill matches."""
    recommendations = []

    for item in pre_ranked:
        if not item.get("has_skill_match"):
            continue

        keyword_score = item["keyword_score"]
        skills_score = max(keyword_score, 55.0)

        _append_recommendation(
            recommendations,
            agent=agent,
            offer=item["offer"],
            item=item,
            agent_skill_tokens=agent_skill_tokens,
            skills_score=skills_score,
            embedding_score=keyword_score,
            keyword_score=keyword_score,
        )

    return recommendations


def recommend_offers_for_agent(agent, offers, sort_mode=SORT_LOCATION_SKILLS):
    if sort_mode not in (SORT_LOCATION_SKILLS, SORT_MATCH_SCORE):
        sort_mode = SORT_LOCATION_SKILLS

    offer_list = list(offers)
    if not offer_list:
        return []

    # ── Phase 1: location + keyword only (instant) ──────────────────────────
    pre_ranked, agent_skill_tokens = _pre_rank_offers_by_location(agent, offer_list)
    nlp_candidates = _select_nlp_candidates(pre_ranked)

    if not nlp_candidates:
        return sort_recommendations(
            _build_keyword_only_recommendations(agent, pre_ranked, agent_skill_tokens),
            sort_mode=sort_mode,
        )

    # ── Phase 2: NLP skills embeddings (only on nearby/pre-qualified offers) ─
    recommendations = []

    try:
        agent_skills_text = build_agent_skills_text(agent)
        agent_skills_embedding = generate_embedding(agent_skills_text)

        offer_skill_texts = [
            build_offer_skills_text(item["offer"]) for item in nlp_candidates
        ]
        offer_skill_embeddings = generate_embeddings_batch(offer_skill_texts)

        for index, item in enumerate(nlp_candidates):
            offer = item["offer"]
            keyword_score = item["keyword_score"]

            embedding_score = (
                cosine_similarity_score(
                    agent_skills_embedding,
                    offer_skill_embeddings[index],
                )
                * 100
            )

            skills_score = combine_skills_score(embedding_score, keyword_score)

            _append_recommendation(
                recommendations,
                agent=agent,
                offer=offer,
                item=item,
                agent_skill_tokens=agent_skill_tokens,
                skills_score=skills_score,
                embedding_score=embedding_score,
                keyword_score=keyword_score,
            )
    except (EmbeddingTimeoutError, Exception):
        recommendations = []

    if not recommendations:
        recommendations = _build_keyword_only_recommendations(
            agent,
            pre_ranked,
            agent_skill_tokens,
        )

    return sort_recommendations(recommendations, sort_mode=sort_mode)