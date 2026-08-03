"""
Cost estimator for ClearSlate runs.
Spec 1.10: page heuristic + per-category element pricing under spec caps.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Literal

from clearslate.config import settings
from clearslate.models import CostEstimate, ElementCategory

# Constants per spec 1.10
ELEMENTS_PER_PAGE = 1.6
# Blended: ~80% turbo @$0.001 + ~20% advanced @$0.005 (live prices verified 2026-08-03)
SEARCH_PRICE_USD = 0.002
TASK_BASE_PRICE_USD = 0.01  # live: base processor $10/1K runs (verified 2026-08-03)
GEMINI_FLASH_USD_PER_M_IN = 1.50  # gemini-3.6-flash, verified 2026-08-03
GEMINI_FLASH_USD_PER_M_OUT = 7.50  # gemini-3.6-flash, verified 2026-08-03
TOKENS_PER_PAGE = 350

# Search requests per element by category
SEARCHES_PER_ELEMENT: dict[ElementCategory, float] = {
    ElementCategory.CHARACTER_NAME: 2.0,
    ElementCategory.BUSINESS_ORG: 2.0,
    ElementCategory.PRODUCT_BRAND: 2.0,
    ElementCategory.PHONE_URL_EMAIL: 0.3,
    ElementCategory.LOCATION_ADDRESS: 1.0,
    ElementCategory.REFERENCED_WORK: 1.0,
    ElementCategory.REAL_PERSON: 1.0,
    ElementCategory.ON_SCREEN_TEXT: 1.0,
    ElementCategory.VEHICLE_IDENTIFIER: 1.0,
}

# Task probability by category
TASK_PROBABILITY: dict[ElementCategory, float] = {
    ElementCategory.REAL_PERSON: 1.0,
    ElementCategory.CHARACTER_NAME: 0.15,
    ElementCategory.BUSINESS_ORG: 0.10,
    ElementCategory.PRODUCT_BRAND: 0.10,
}

# Average distribution of elements across categories for page-based estimation
AVERAGE_MIX: dict[ElementCategory, float] = {
    ElementCategory.CHARACTER_NAME: 0.30,
    ElementCategory.BUSINESS_ORG: 0.15,
    ElementCategory.LOCATION_ADDRESS: 0.12,
    ElementCategory.ON_SCREEN_TEXT: 0.12,
    ElementCategory.PRODUCT_BRAND: 0.10,
    ElementCategory.REFERENCED_WORK: 0.08,
    ElementCategory.PHONE_URL_EMAIL: 0.06,
    ElementCategory.REAL_PERSON: 0.04,
    ElementCategory.VEHICLE_IDENTIFIER: 0.03,
}


def _estimate(
    counts: Mapping[ElementCategory, int],
    page_count: int,
    basis: Literal["pages", "elements"],
    element_count_override: int | None = None,
) -> CostEstimate:
    """Internal helper for cost estimation with optional element_count override.

    Args:
        counts: Mapping of ElementCategory to count
        page_count: Number of pages
        basis: "pages" or "elements"
        element_count_override: If provided, use this instead of sum(counts.values())

    Returns:
        CostEstimate with all fields populated
    """
    # Calculate element count
    if element_count_override is not None:
        element_count = element_count_override
    else:
        element_count = sum(counts.values())

    # Calculate search requests: ceil(sum of counts * SEARCHES_PER_ELEMENT[category])
    search_requests = math.ceil(
        sum(n * SEARCHES_PER_ELEMENT[c] for c, n in counts.items())
    )

    # Calculate task runs: min(ceil(sum of counts * TASK_PROBABILITY.get(category, 0.0)), 40)
    task_runs = min(
        math.ceil(sum(n * TASK_PROBABILITY.get(c, 0.0) for c, n in counts.items())),
        settings.max_task_runs,
    )

    # Calculate Gemini costs
    gemini_in = page_count * TOKENS_PER_PAGE
    gemini_out = 0.6 * gemini_in
    gemini_usd = round(
        (gemini_in * GEMINI_FLASH_USD_PER_M_IN + gemini_out * GEMINI_FLASH_USD_PER_M_OUT)
        / 1_000_000,
        4,
    )

    # Calculate parallel (search + task) costs
    parallel_usd = round(
        search_requests * SEARCH_PRICE_USD + task_runs * TASK_BASE_PRICE_USD,
        4,
    )

    # Calculate total
    total_usd = round(gemini_usd + parallel_usd, 4)

    return CostEstimate(
        element_count=element_count,
        search_requests=search_requests,
        task_runs=task_runs,
        gemini_usd=gemini_usd,
        parallel_usd=parallel_usd,
        total_usd=total_usd,
        basis=basis,
    )


def estimate_cost(
    counts: Mapping[ElementCategory, int],
    page_count: int,
) -> CostEstimate:
    """Estimate cost based on element category counts.

    Args:
        counts: Mapping of ElementCategory to element count
        page_count: Number of pages in the document

    Returns:
        CostEstimate with basis="elements"
    """
    return _estimate(counts, page_count, basis="elements")


def estimate_from_pages(page_count: int) -> CostEstimate:
    """Estimate cost based on page count alone, using average element distribution.

    Args:
        page_count: Number of pages

    Returns:
        CostEstimate with basis="pages"
    """
    # Calculate estimated element count
    est_elements = int(page_count * ELEMENTS_PER_PAGE)

    # Distribute across categories proportional to AVERAGE_MIX
    counts = {c: round(est_elements * f) for c, f in AVERAGE_MIX.items()}

    # Call internal helper with element_count_override to ensure it matches est_elements
    return _estimate(counts, page_count, basis="pages", element_count_override=est_elements)
