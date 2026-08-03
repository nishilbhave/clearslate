"""Deduplication of extracted elements across chunks."""
from collections import defaultdict

from pydantic import BaseModel

from clearslate.breakdown.normalize import normalize_text
from clearslate.models import Element, ElementCategory


class RawExtractedElement(BaseModel):
    """
    Raw extracted element with provenance information, before deduplication.

    Attributes:
        category: The ElementCategory of this element
        text: The original text as extracted
        pages: List of page numbers where this element appears (1-indexed)
        scene: Optional scene identifier
        context_snippet: Context snippet where the element appears
        chunk_index: 0-based index of the chunk this element came from
    """

    category: ElementCategory
    text: str
    pages: list[int]
    scene: str | None
    context_snippet: str
    chunk_index: int


def dedupe_elements(raw: list[RawExtractedElement]) -> list[Element]:
    """
    Deduplicate elements across chunks, merging page information.

    Groups elements by (category, normalized_text). For each group:
    - Merges pages into sorted set union
    - Uses text/scene/context_snippet from occurrence with lowest first page
      (tie-break by lowest chunk_index)
    - Generates sequential IDs (el_0001, el_0002, ...)
    - Sorts output by (min(pages), category.value)

    Args:
        raw: List of RawExtractedElement objects from various chunks

    Returns:
        List of deduplicated Element objects with merged pages
    """
    if not raw:
        return []

    # Group by (category, normalized_text)
    groups: defaultdict[tuple[ElementCategory, str], list[RawExtractedElement]] = (
        defaultdict(list)
    )

    for element in raw:
        normalized = normalize_text(element.text, element.category)
        key = (element.category, normalized)
        groups[key].append(element)

    # Build merged elements
    merged: list[tuple[Element, int]] = []  # (element, min_page_for_sorting)

    for (category, normalized_text), elements in groups.items():
        # Merge pages: sorted set union
        all_pages = set()
        for elem in elements:
            all_pages.update(elem.pages)
        merged_pages = sorted(all_pages)

        # Find representative occurrence: lowest min(pages), then lowest chunk_index
        representative = min(
            elements,
            key=lambda e: (min(e.pages), e.chunk_index),
        )

        # Create Element
        element = Element(
            id="",  # Will be assigned after sorting
            category=category,
            text=representative.text,
            normalized_text=normalized_text,
            pages=merged_pages,
            scene=representative.scene,
            context_snippet=representative.context_snippet,
        )

        min_page = min(merged_pages)
        merged.append((element, min_page))

    # Sort by (min_page, category.value)
    merged.sort(key=lambda x: (x[1], x[0].category.value))

    # Assign sequential IDs and return
    result = []
    for idx, (element, _) in enumerate(merged, 1):
        element.id = f"el_{idx:04d}"
        result.append(element)

    return result
