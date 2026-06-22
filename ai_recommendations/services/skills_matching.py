import re


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

SKILL_SPLIT_PATTERN = re.compile(r"[,;/|\n]+")

STOP_WORDS = {
    "and",
    "or",
    "the",
    "for",
    "with",
    "des",
    "les",
    "une",
    "dans",
    "pour",
    "sur",
}


def parse_skill_tokens(*texts):
    tokens = []

    for text in texts:
        if not text:
            continue

        parts = SKILL_SPLIT_PATTERN.split(str(text).lower())

        for part in parts:
            token = part.strip()
            token = re.sub(r"\s+", " ", token)

            if len(token) < 2:
                continue

            if token in STOP_WORDS:
                continue

            tokens.append(token)

    # Preserve order, remove duplicates.
    seen = set()
    unique = []

    for token in tokens:
        if token in seen:
            continue

        seen.add(token)
        unique.append(token)

    return unique


def get_agent_skill_tokens(agent):
    profile = get_profile(agent)

    if not profile:
        return []

    skills = safe_value(getattr(profile, "skills", ""))
    bio = safe_value(getattr(profile, "bio", ""))

    return parse_skill_tokens(skills, bio)


def build_agent_skills_text(agent):
    profile = get_profile(agent)

    if not profile:
        return ""

    skills = safe_value(getattr(profile, "skills", ""))
    bio = safe_value(getattr(profile, "bio", ""))

    return f"""
    Agent skills and expertise:
    Skills: {skills}
    Professional bio: {bio}
    """


def build_offer_skills_text(offer):
    title = safe_value(getattr(offer, "title", ""))
    description = safe_value(getattr(offer, "description", ""))

    category_name = ""
    category_description = ""

    category = getattr(offer, "category", None)
    if category:
        category_name = safe_value(getattr(category, "name", ""))
        category_description = safe_value(getattr(category, "description", ""))

    return f"""
    Job offer:
    Title: {title}
    Description: {description}
    Category: {category_name}
    Category details: {category_description}
    Required skills and tasks: {title}, {description}, {category_name}
    """


def get_offer_category_name(offer):
    category = getattr(offer, "category", None)
    if not category:
        return ""

    return safe_value(getattr(category, "name", "")).strip()


def get_offer_search_corpus(offer):
    title = safe_value(getattr(offer, "title", ""))
    description = safe_value(getattr(offer, "description", ""))
    category_name = get_offer_category_name(offer)

    return " ".join(
        part.lower()
        for part in [title, description, category_name]
        if part
    )


def get_matched_skill_tokens(agent_tokens, offer_corpus, category_name=""):
    if not agent_tokens:
        return []

    category_lower = category_name.lower().strip()
    matched = []

    for token in agent_tokens:
        if token in offer_corpus:
            matched.append(token)
            continue

        if category_lower and (
            token == category_lower
            or token in category_lower
            or category_lower in token
        ):
            matched.append(token)
            continue

        if " " in token and token in offer_corpus:
            matched.append(token)
            continue

        for word in token.split():
            if len(word) >= 3 and word in offer_corpus:
                matched.append(token)
                break

    return matched


def compute_keyword_skills_score(agent_tokens, offer_corpus, category_name=""):
    if not agent_tokens:
        return 0.0

    matched = get_matched_skill_tokens(
        agent_tokens,
        offer_corpus,
        category_name=category_name,
    )

    if not matched:
        return 0.0

    coverage = len(matched) / len(agent_tokens)
    base = min(100.0, coverage * 100.0)

    category_lower = category_name.lower().strip()
    if category_lower and any(
        token == category_lower or category_lower in token or token in category_lower
        for token in agent_tokens
    ):
        base = min(100.0, max(base, 85.0))

    if len(matched) >= 2:
        base = min(100.0, base + 10.0)

    if len(matched) >= 3:
        base = min(100.0, base + 5.0)

    return round(base, 2)


def combine_skills_score(embedding_score, keyword_score):
    if keyword_score <= 0:
        return round(embedding_score, 2)

    if embedding_score <= 0:
        return round(keyword_score, 2)

    combined = (embedding_score * 0.5) + (keyword_score * 0.5)

    # Direct skill/category match must not be erased by a weak embedding.
    if keyword_score >= 70:
        combined = max(combined, keyword_score * 0.92)

    if keyword_score >= 50 and embedding_score < keyword_score:
        combined = max(combined, keyword_score * 0.85)

    return round(min(combined, 100.0), 2)


def get_minimum_skills_score(location_tier, keyword_score=0.0, has_skill_match=False):
    # Tier values: 3 same city, 2 nearby, 1 other, 0 unknown.
    if has_skill_match or keyword_score >= 50:
        if location_tier == 3:
            return 25.0
        if location_tier == 2:
            return 30.0
        if location_tier == 1:
            return 32.0
        return 35.0

    if location_tier == 3:
        return 32.0

    if location_tier == 2:
        return 38.0

    if location_tier == 1:
        return 42.0

    return 45.0


def passes_skills_filter(skills_score, location_tier, keyword_score, has_skill_match):
    minimum = get_minimum_skills_score(
        location_tier,
        keyword_score=keyword_score,
        has_skill_match=has_skill_match,
    )

    if skills_score >= minimum:
        return True

    # Always allow clear skill/category agreement in local area.
    if has_skill_match and keyword_score >= 40 and location_tier >= 2:
        return True

    return False


def build_skills_reasons(agent_tokens, offer_corpus, skills_score, category_name=""):
    reasons = []

    matched = get_matched_skill_tokens(
        agent_tokens,
        offer_corpus,
        category_name=category_name,
    )

    if matched:
        preview = ", ".join(matched[:4])
        reasons.append(f"Matches your skills: {preview}.")

    if skills_score >= 65:
        reasons.append(
            "Strong alignment between your skills/bio and this offer's title, category, and description."
        )
    elif skills_score >= 45:
        reasons.append(
            "Good skills fit with the offer requirements based on your profile."
        )

    return reasons
