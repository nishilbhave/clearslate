"""Tests for dedupe_elements function."""
from clearslate.breakdown.dedupe import RawExtractedElement, dedupe_elements
from clearslate.models import ElementCategory


class TestDedupeElementsRequired:
    """Required test cases from the brief."""

    def test_same_name_different_pages_different_chunks(self):
        """Same name on pages [1] and [40] with different chunks → one element pages==[1,40]"""
        raw = [
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="John Smith",
                pages=[1],
                scene=None,
                context_snippet="John Smith enters the room",
                chunk_index=0,
            ),
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="john smith",  # Different case
                pages=[40],
                scene=None,
                context_snippet="John Smith leaves the room",
                chunk_index=4,
            ),
        ]
        result = dedupe_elements(raw)
        assert len(result) == 1
        assert result[0].id == "el_0001"
        assert result[0].pages == [1, 40]
        assert result[0].category == ElementCategory.CHARACTER_NAME
        assert result[0].normalized_text == "john smith"
        # Text should be from the occurrence with the lowest first page
        assert result[0].text == "John Smith"
        assert result[0].context_snippet == "John Smith enters the room"

    def test_same_text_different_categories(self):
        """Same text in CHARACTER_NAME and BUSINESS_ORG → two elements"""
        raw = [
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="Smith",
                pages=[5],
                scene=None,
                context_snippet="Character Smith appears",
                chunk_index=0,
            ),
            RawExtractedElement(
                category=ElementCategory.BUSINESS_ORG,
                text="Smith",
                pages=[5],
                scene=None,
                context_snippet="The Smith Company",
                chunk_index=0,
            ),
        ]
        result = dedupe_elements(raw)
        assert len(result) == 2
        # Should be sorted by (min(pages), category.value)
        # CHARACTER_NAME < BUSINESS_ORG alphabetically
        assert result[0].category == ElementCategory.BUSINESS_ORG
        assert result[0].id == "el_0001"
        assert result[1].category == ElementCategory.CHARACTER_NAME
        assert result[1].id == "el_0002"

    def test_duplicate_pages_single_page_listed_once(self):
        """Two chunks both reporting page 11 for the same element → page listed once"""
        raw = [
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="Alice",
                pages=[11],
                scene=None,
                context_snippet="Alice talks",
                chunk_index=0,
            ),
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="Alice",
                pages=[11],
                scene=None,
                context_snippet="Alice listens",
                chunk_index=1,
            ),
        ]
        result = dedupe_elements(raw)
        assert len(result) == 1
        assert result[0].pages == [11]
        assert result[0].id == "el_0001"


class TestDedupeElementsOrdering:
    """Tests for output ordering by (min(pages), category.value)."""

    def test_order_by_min_page_first(self):
        """Elements should be ordered by min page number first."""
        raw = [
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="Bob",
                pages=[20],
                scene=None,
                context_snippet="Bob",
                chunk_index=0,
            ),
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="Alice",
                pages=[5],
                scene=None,
                context_snippet="Alice",
                chunk_index=0,
            ),
        ]
        result = dedupe_elements(raw)
        assert result[0].text == "Alice"
        assert result[1].text == "Bob"
        assert result[0].id == "el_0001"
        assert result[1].id == "el_0002"

    def test_order_by_category_when_same_page(self):
        """When min pages are equal, order by category.value alphabetically."""
        raw = [
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="Test1",
                pages=[10],
                scene=None,
                context_snippet="Test1",
                chunk_index=0,
            ),
            RawExtractedElement(
                category=ElementCategory.BUSINESS_ORG,
                text="Test2",
                pages=[10],
                scene=None,
                context_snippet="Test2",
                chunk_index=0,
            ),
        ]
        result = dedupe_elements(raw)
        # BUSINESS_ORG < CHARACTER_NAME alphabetically
        assert result[0].category == ElementCategory.BUSINESS_ORG
        assert result[1].category == ElementCategory.CHARACTER_NAME


class TestDedupeElementsIdGeneration:
    """Tests for ID generation."""

    def test_ids_sequential_el_0001_format(self):
        """IDs should be generated as el_0001, el_0002, etc."""
        raw = [
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text=f"Char{i}",
                pages=[i],
                scene=None,
                context_snippet=f"Character {i}",
                chunk_index=0,
            )
            for i in range(1, 6)
        ]
        result = dedupe_elements(raw)
        assert len(result) == 5
        for i, elem in enumerate(result, 1):
            assert elem.id == f"el_{i:04d}"


class TestDedupeElementsRepresentativeSelection:
    """Tests for selecting representative text/scene/context from lowest page."""

    def test_representative_from_lowest_page(self):
        """When multiple occurrences, use text/scene/snippet from lowest page."""
        raw = [
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="John",
                pages=[50],
                scene="Scene 3",
                context_snippet="John on page 50",
                chunk_index=2,
            ),
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="John",
                pages=[10],
                scene="Scene 1",
                context_snippet="John on page 10",
                chunk_index=0,
            ),
        ]
        result = dedupe_elements(raw)
        assert len(result) == 1
        assert result[0].text == "John"
        assert result[0].scene == "Scene 1"
        assert result[0].context_snippet == "John on page 10"

    def test_representative_tiebreak_by_chunk_index(self):
        """When pages are equal, use lowest chunk_index."""
        raw = [
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="John",
                pages=[10],
                scene="Scene 2",
                context_snippet="John in chunk 2",
                chunk_index=2,
            ),
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="John",
                pages=[10],
                scene="Scene 0",
                context_snippet="John in chunk 0",
                chunk_index=0,
            ),
        ]
        result = dedupe_elements(raw)
        assert len(result) == 1
        assert result[0].scene == "Scene 0"
        assert result[0].context_snippet == "John in chunk 0"


class TestDedupeElementsNormalization:
    """Tests for normalized_text generation."""

    def test_normalized_text_from_normalization(self):
        """normalized_text should be the normalized form of the text."""
        raw = [
            RawExtractedElement(
                category=ElementCategory.BUSINESS_ORG,
                text="The Apple Inc.",
                pages=[1],
                scene=None,
                context_snippet="Apple",
                chunk_index=0,
            ),
        ]
        result = dedupe_elements(raw)
        assert result[0].text == "The Apple Inc."
        # Should normalize: lowercase, remove period, remove leading "the"
        assert result[0].normalized_text == "apple inc"

    def test_normalized_text_phone_number(self):
        """Phone numbers should be normalized to digits only."""
        raw = [
            RawExtractedElement(
                category=ElementCategory.PHONE_URL_EMAIL,
                text="(415) 867-5309",
                pages=[1],
                scene=None,
                context_snippet="Phone",
                chunk_index=0,
            ),
        ]
        result = dedupe_elements(raw)
        assert result[0].normalized_text == "4158675309"


class TestDedupeElementsPageMerging:
    """Tests for page set union merging."""

    def test_page_union_merge(self):
        """Pages from multiple occurrences should be merged into sorted set union."""
        raw = [
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="John",
                pages=[5, 10, 15],
                scene=None,
                context_snippet="John",
                chunk_index=0,
            ),
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="John",
                pages=[8, 12, 20],
                scene=None,
                context_snippet="John",
                chunk_index=1,
            ),
        ]
        result = dedupe_elements(raw)
        assert len(result) == 1
        assert result[0].pages == [5, 8, 10, 12, 15, 20]

    def test_page_union_no_duplicates(self):
        """Page union should not have duplicates."""
        raw = [
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="John",
                pages=[5, 10],
                scene=None,
                context_snippet="John",
                chunk_index=0,
            ),
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="John",
                pages=[5, 10, 15],
                scene=None,
                context_snippet="John",
                chunk_index=1,
            ),
        ]
        result = dedupe_elements(raw)
        assert result[0].pages == [5, 10, 15]

    def test_page_union_sorted(self):
        """Page union should be sorted."""
        raw = [
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="John",
                pages=[20, 10],
                scene=None,
                context_snippet="John",
                chunk_index=0,
            ),
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="John",
                pages=[15, 5],
                scene=None,
                context_snippet="John",
                chunk_index=1,
            ),
        ]
        result = dedupe_elements(raw)
        assert result[0].pages == [5, 10, 15, 20]


class TestDedupeElementsEmpty:
    """Tests for edge cases."""

    def test_empty_input(self):
        """Empty input should return empty list."""
        result = dedupe_elements([])
        assert result == []

    def test_single_element(self):
        """Single element should return as-is with el_0001 id."""
        raw = [
            RawExtractedElement(
                category=ElementCategory.CHARACTER_NAME,
                text="John",
                pages=[5],
                scene=None,
                context_snippet="John",
                chunk_index=0,
            ),
        ]
        result = dedupe_elements(raw)
        assert len(result) == 1
        assert result[0].id == "el_0001"
        assert result[0].status.value == "pending"  # Default status
