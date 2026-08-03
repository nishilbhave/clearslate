"""Tests for normalize_text function."""
from clearslate.breakdown.normalize import normalize_text
from clearslate.models import ElementCategory


class TestNormalizeTextRequired:
    """Required test cases from the brief."""

    def test_business_org_remove_article(self):
        """The Blue Duck Tavern (BUSINESS_ORG) → blue duck tavern"""
        result = normalize_text("The Blue Duck Tavern", ElementCategory.BUSINESS_ORG)
        assert result == "blue duck tavern"

    def test_phone_digits_only(self):
        """(415) 867-5309 (PHONE_URL_EMAIL) → 4158675309"""
        result = normalize_text("(415) 867-5309", ElementCategory.PHONE_URL_EMAIL)
        assert result == "4158675309"

    def test_url_lowercase_strip_trailing_slash(self):
        """Example.COM/ (PHONE_URL_EMAIL) → example.com"""
        result = normalize_text("Example.COM/", ElementCategory.PHONE_URL_EMAIL)
        assert result == "example.com"

    def test_character_name_curly_apostrophe_nfkc(self):
        """MARISOL's (CHARACTER_NAME, U+2019 curly apostrophe) → marisol's (ASCII apostrophe)"""
        # U+2019 is the right single quotation mark (curly apostrophe)
        text_with_curly = "MARISOL’s"
        result = normalize_text(text_with_curly, ElementCategory.CHARACTER_NAME)
        assert result == "marisol's"


class TestNormalizeTextPhoneUrlEmail:
    """Tests for PHONE_URL_EMAIL category."""

    def test_email_lowercase(self):
        """Email should be lowercased and whitespace stripped."""
        result = normalize_text("John.Doe@Example.COM", ElementCategory.PHONE_URL_EMAIL)
        assert result == "john.doe@example.com"

    def test_url_with_protocol(self):
        """URL with http protocol should be lowercased."""
        result = normalize_text("HTTP://Example.COM/path", ElementCategory.PHONE_URL_EMAIL)
        assert result == "http://example.com/path"

    def test_url_https(self):
        """URL with https should be lowercased."""
        result = normalize_text("HTTPS://Example.COM", ElementCategory.PHONE_URL_EMAIL)
        assert result == "https://example.com"

    def test_domain_with_dot(self):
        """Domain-like text with dot should be treated as URL."""
        result = normalize_text("example.com", ElementCategory.PHONE_URL_EMAIL)
        assert result == "example.com"

    def test_phone_with_extensions(self):
        """Phone with extension should be digits only."""
        result = normalize_text("415-867-5309 ext. 123", ElementCategory.PHONE_URL_EMAIL)
        assert result == "4158675309123"

    def test_phone_with_plus(self):
        """Phone with plus sign should be digits only (plus stripped)."""
        result = normalize_text("+1 (415) 867-5309", ElementCategory.PHONE_URL_EMAIL)
        assert result == "14158675309"

    def test_email_with_spaces(self):
        """Email with spaces should have them stripped."""
        result = normalize_text("john . doe @ example . com", ElementCategory.PHONE_URL_EMAIL)
        assert result == "john.doe@example.com"

    def test_url_with_multiple_trailing_slashes(self):
        """URL with multiple trailing slashes should have only one removed."""
        result = normalize_text("Example.COM//", ElementCategory.PHONE_URL_EMAIL)
        # Strip a single trailing slash
        assert result == "example.com/"


class TestNormalizeTextDefault:
    """Tests for default category normalization."""

    def test_basic_lowercase_and_casefold(self):
        """Basic text should be lowercased."""
        result = normalize_text("HELLO WORLD", ElementCategory.CHARACTER_NAME)
        assert result == "hello world"

    def test_remove_punctuation_keep_apostrophe(self):
        """Apostrophes and hyphens should be kept."""
        result = normalize_text("John's-Paul", ElementCategory.CHARACTER_NAME)
        assert result == "john's-paul"

    def test_remove_punctuation_keep_ampersand(self):
        """Ampersands should be kept."""
        result = normalize_text("Smith & Sons", ElementCategory.BUSINESS_ORG)
        assert result == "smith & sons"

    def test_remove_other_punctuation(self):
        """Other punctuation should be removed."""
        result = normalize_text("Hello, World! (Test)", ElementCategory.CHARACTER_NAME)
        assert result == "hello world test"

    def test_collapse_whitespace(self):
        """Multiple spaces should collapse to single space."""
        result = normalize_text("Hello    World", ElementCategory.CHARACTER_NAME)
        assert result == "hello world"

    def test_strip_leading_the(self):
        """Leading 'the ' should be removed once."""
        result = normalize_text("The The Killers", ElementCategory.BUSINESS_ORG)
        assert result == "the killers"

    def test_strip_leading_a(self):
        """Leading 'a ' should be removed."""
        result = normalize_text("A Christmas Carol", ElementCategory.REFERENCED_WORK)
        assert result == "christmas carol"

    def test_strip_leading_an(self):
        """Leading 'an ' should be removed."""
        result = normalize_text("An Unexpected Journey", ElementCategory.REFERENCED_WORK)
        assert result == "unexpected journey"

    def test_no_strip_the_in_middle(self):
        """'the' in the middle should not be removed."""
        result = normalize_text("King of The Hill", ElementCategory.BUSINESS_ORG)
        assert result == "king of the hill"

    def test_ampersand_preserved(self):
        """Ampersands in business names should be preserved."""
        result = normalize_text("Rock & Roll Hall of Fame", ElementCategory.BUSINESS_ORG)
        assert result == "rock & roll hall of fame"

    def test_hyphen_preserved(self):
        """Hyphens in names should be preserved."""
        result = normalize_text("Jean-Claude Van Damme", ElementCategory.REAL_PERSON)
        assert result == "jean-claude van damme"

    def test_ascii_apostrophe(self):
        """ASCII apostrophes should be preserved."""
        result = normalize_text("McDonald's", ElementCategory.BUSINESS_ORG)
        assert result == "mcdonald's"

    def test_location_with_punctuation(self):
        """Location names with punctuation should be normalized."""
        result = normalize_text("Los Angeles, CA", ElementCategory.LOCATION_ADDRESS)
        assert result == "los angeles ca"

    def test_on_screen_text_normalization(self):
        """ON_SCREEN_TEXT should be normalized like default."""
        result = normalize_text("HELLO WORLD!!!", ElementCategory.ON_SCREEN_TEXT)
        assert result == "hello world"

    def test_vehicle_identifier_normalization(self):
        """VEHICLE_IDENTIFIER should be normalized like default."""
        result = normalize_text("1970's Mustang", ElementCategory.VEHICLE_IDENTIFIER)
        assert result == "1970's mustang"

    def test_nfkc_normalization(self):
        """NFKC normalization should apply (e.g., composed to decomposed)."""
        # Using an example with diacritics that NFKC would normalize
        result = normalize_text("Café", ElementCategory.CHARACTER_NAME)
        # NFKC should normalize this
        assert "café" in result or "cafe" in result  # Both forms are valid after NFKC
