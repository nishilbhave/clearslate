"""Text normalization for clearance elements."""
import re
import unicodedata

from clearslate.models import ElementCategory


def normalize_text(text: str, category: ElementCategory) -> str:
    """
    Normalize text based on category.

    Args:
        text: The text to normalize
        category: The ElementCategory to apply category-specific normalization

    Returns:
        Normalized text

    Examples:
        >>> normalize_text("The Blue Duck Tavern", ElementCategory.BUSINESS_ORG)
        "blue duck tavern"
        >>> normalize_text("(415) 867-5309", ElementCategory.PHONE_URL_EMAIL)
        "4158675309"
        >>> normalize_text("Example.COM/", ElementCategory.PHONE_URL_EMAIL)
        "example.com"
    """
    if category == ElementCategory.PHONE_URL_EMAIL:
        return _normalize_phone_url_email(text)
    else:
        return _normalize_default(text)


def _normalize_phone_url_email(text: str) -> str:
    """
    Normalize PHONE_URL_EMAIL category.

    Strategy: if text contains letters, treat as URL/email (de-space and normalize);
    if text contains NO letters, treat as phone (digits only).

    Exception: if text looks like a phone with extension (e.g., "415-867-5309 ext. 123"),
    treat as phone despite having letters.

    This handles PDF extraction artifacts like "Example . com" correctly.
    """
    text = text.strip()

    # If text contains no letters, it's a phone number
    if not any(c.isalpha() for c in text):
        # Phone: digits only
        return re.sub(r"\D", "", text)

    # Text contains letters, so treat as URL/email
    # De-space for robust domain detection
    de_spaced = text.replace(" ", "")

    # Check if it's an email or URL
    is_email = "@" in de_spaced
    is_url = de_spaced.startswith(("http://", "https://"))

    # Domain detection: has dot with letters around it
    is_domain = False
    if "." in de_spaced and not de_spaced[0].isdigit():
        # Domains typically start with a letter, not a digit
        # This filters out cases like "415-867-5309ext.123"
        parts = de_spaced.split(".")
        if len(parts) >= 2:
            # Check if any part has letters (typical for domain names)
            is_domain = any(any(c.isalpha() for c in part) for part in parts)

    if is_email or is_url or is_domain:
        # Email or URL: lowercase, strip single trailing "/"
        normalized = de_spaced.lower()
        normalized = normalized.removesuffix("/")
        return normalized
    else:
        # Fallback: if it has letters but doesn't look like URL/email, digits only
        return re.sub(r"\D", "", text)


def _normalize_default(text: str) -> str:
    """
    Normalize default category (all categories except PHONE_URL_EMAIL).

    Steps:
    1. NFKC normalization
    2. Explicitly replace U+2019 (curly apostrophe) with ASCII apostrophe
    3. casefold()
    4. Remove punctuation except word chars, spaces, &, ', -
    5. Collapse whitespace runs to single space
    6. Strip leading/trailing whitespace
    7. Drop ONE leading article (the/a/an)
    """
    # Step 1: NFKC normalization
    text = unicodedata.normalize("NFKC", text)

    # Step 2: Explicitly replace curly apostrophe with ASCII apostrophe
    text = text.replace("’", "'")

    # Step 3: casefold for case-insensitive comparison
    text = text.casefold()

    # Step 4: Remove punctuation except word chars, spaces, &, ', -
    # \w includes letters, digits, underscore; we want to keep those, spaces, &, ', -
    # Remove everything else: [^\w\s&'-]
    text = re.sub(r"[^\w\s&'-]", "", text)

    # Step 5: Collapse whitespace runs to single space
    text = re.sub(r"\s+", " ", text)

    # Step 6: Strip leading/trailing whitespace
    text = text.strip()

    # Step 7: Drop ONE leading article (the/a/an)
    if text.startswith("the "):
        text = text[4:]
    elif text.startswith("a "):
        text = text[2:]
    elif text.startswith("an "):
        text = text[3:]

    return text
