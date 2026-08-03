"""Matching + metrics for the golden-script extraction eval (Task 1.12).

Pure functions only — no filesystem/manifest paths here. Callers (the offline
eval test, `scripts/record_golden_fixtures.py`'s sibling `run_golden_live.py`)
own their own paths to `tests/golden/manifest.json` and the fixture directory,
mirroring `scripts/check_manifest.py`'s pattern.

A `plant` is one entry from `tests/golden/manifest.json["plants"]`:
`{"plant_id", "category", "surface_text", "match_aliases", "expected_pages", ...}`.
"""
from __future__ import annotations

from dataclasses import dataclass

from clearslate.breakdown.normalize import normalize_text
from clearslate.models import Element, ElementCategory


@dataclass(frozen=True)
class PlantMatch:
    """One golden-manifest plant successfully matched to an extracted element."""

    plant_id: str
    matched_element_id: str
    page_hit: bool  # True iff the element's pages intersect the plant's expected_pages


@dataclass(frozen=True)
class GoldenMetrics:
    recall: float  # len(matched) / len(plants)
    page_hit_rate: float  # matched-with-page-hit / len(matched); 0.0 if nothing matched
    element_count: int
    categories_present: set[ElementCategory]
    matched: list[PlantMatch]
    missed_plant_ids: list[str]  # plants with no matching element, in manifest order


def match_plants(plants: list[dict], elements: list[Element]) -> list[PlantMatch]:
    """Match golden-manifest plants against extracted elements.

    A plant matches an element iff:
      - `element.category.value == plant["category"]`, AND
      - for ANY alias in `plant["match_aliases"]`: that alias, normalized under the
        plant's category, either equals `element.normalized_text`, is a substring of
        it, or contains it.

    Returns one `PlantMatch` per matched plant (the first matching element found, in
    `elements` order) — unmatched plants are simply omitted, so
    `recall = len(match_plants(...)) / len(plants)`.
    """
    matches: list[PlantMatch] = []
    for plant in plants:
        category = plant["category"]
        normalized_aliases = [
            normalize_text(alias, ElementCategory(category)) for alias in plant["match_aliases"]
        ]

        matched_element: Element | None = None
        for element in elements:
            if element.category.value != category:
                continue
            for normalized_alias in normalized_aliases:
                if not normalized_alias:
                    continue
                if (
                    element.normalized_text == normalized_alias
                    or normalized_alias in element.normalized_text
                    or element.normalized_text in normalized_alias
                ):
                    matched_element = element
                    break
            if matched_element is not None:
                break

        if matched_element is not None:
            page_hit = bool(set(matched_element.pages) & set(plant["expected_pages"]))
            matches.append(
                PlantMatch(
                    plant_id=plant["plant_id"],
                    matched_element_id=matched_element.id,
                    page_hit=page_hit,
                )
            )
    return matches


def compute_metrics(plants: list[dict], elements: list[Element]) -> GoldenMetrics:
    """Compute the Task 1.12 eval metrics: recall, page-hit rate, count, categories."""
    matches = match_plants(plants, elements)
    matched_ids = {m.plant_id for m in matches}
    missed_plant_ids = [p["plant_id"] for p in plants if p["plant_id"] not in matched_ids]

    recall = len(matches) / len(plants) if plants else 0.0
    hits = sum(1 for m in matches if m.page_hit)
    page_hit_rate = hits / len(matches) if matches else 0.0

    return GoldenMetrics(
        recall=recall,
        page_hit_rate=page_hit_rate,
        element_count=len(elements),
        categories_present={e.category for e in elements},
        matched=matches,
        missed_plant_ids=missed_plant_ids,
    )
