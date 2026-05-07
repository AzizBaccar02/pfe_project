import re


BAD_WORDS = [
    "apple",
    "banana",
    "orange",
    "kiwi",
    "mango",
    "grape",
    "peach",
    "melon",
    "watermelon",
    "strawberry",
]


def moderate_message_content(content):
    if not content:
        return content, False, []

    detected_words = set()

    def replace_bad_word(match):
        detected_words.add(match.group(0).lower())
        return "****"

    moderated_content = content

    for bad_word in BAD_WORDS:
        pattern = r"\b" + re.escape(bad_word) + r"\b"
        moderated_content = re.sub(
            pattern,
            replace_bad_word,
            moderated_content,
            flags=re.IGNORECASE,
        )

    has_warning = len(detected_words) > 0

    return moderated_content, has_warning, sorted(detected_words)


def build_moderation_response_data(data, has_warning, detected_words):
    data["hasWarning"] = has_warning
    data["warningMessage"] = (
        "Please avoid inappropriate language."
        if has_warning
        else None
    )
    data["moderatedWords"] = detected_words

    return data