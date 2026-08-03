"""
Tests for cost estimation module.
Spec 1.10: page heuristic + per-category element pricing under spec caps.
"""
from clearslate.costs import (
    GEMINI_FLASH_USD_PER_M_IN,
    GEMINI_FLASH_USD_PER_M_OUT,
    SEARCH_PRICE_USD,
    TASK_BASE_PRICE_USD,
    estimate_cost,
    estimate_from_pages,
)
from clearslate.models import ElementCategory


def test_estimate_cost_pinned_numbers():
    """Spec pinned test: counts with CHARACTER_NAME, BUSINESS_ORG, PHONE_URL_EMAIL.
    search_requests must be 83; task_runs must be 6; total_usd formula exact."""
    counts = {
        ElementCategory.CHARACTER_NAME: 30,
        ElementCategory.BUSINESS_ORG: 10,
        ElementCategory.PHONE_URL_EMAIL: 10,
    }
    page_count = 100

    estimate = estimate_cost(counts, page_count)

    # Verify pinned search_requests
    assert estimate.search_requests == 83, (
        f"Expected search_requests==83, got {estimate.search_requests}"
    )

    # Verify pinned task_runs
    assert estimate.task_runs == 6, f"Expected task_runs==6, got {estimate.task_runs}"

    # Verify the calculation manually
    # search_requests = ceil(30*2.0 + 10*2.0 + 10*0.3) = ceil(60 + 20 + 3) = 83
    # task_runs = min(ceil(30*0.15 + 10*0.10 + 10*0.0), 40) = min(ceil(4.5 + 1.0), 40) = 6
    # gemini_in = 100 * 350 = 35000 tokens
    # gemini_out = 0.6 * 35000 = 21000 tokens
    # gemini_usd = round(
    #     (35000*GEMINI_FLASH_USD_PER_M_IN + 21000*GEMINI_FLASH_USD_PER_M_OUT) / 1_000_000, 4
    # )
    gemini_in = 100 * 350
    gemini_out = 0.6 * gemini_in
    expected_gemini_usd = round(
        (gemini_in * GEMINI_FLASH_USD_PER_M_IN + gemini_out * GEMINI_FLASH_USD_PER_M_OUT)
        / 1_000_000,
        4,
    )
    # parallel_usd = round(83*SEARCH_PRICE_USD + 6*TASK_BASE_PRICE_USD, 4)
    expected_parallel_usd = round(83 * SEARCH_PRICE_USD + 6 * TASK_BASE_PRICE_USD, 4)
    expected_total_usd = round(expected_gemini_usd + expected_parallel_usd, 4)

    assert estimate.gemini_usd == expected_gemini_usd
    assert estimate.parallel_usd == expected_parallel_usd
    assert estimate.total_usd == expected_total_usd

    # Verify basis
    assert estimate.basis == "elements"
    assert estimate.element_count == 50  # 30 + 10 + 10


def test_estimate_from_pages_130_pages_under_2_dollars():
    """Spec target: 130-page estimate total_usd < $2.00."""
    estimate = estimate_from_pages(130)

    assert estimate.total_usd < 2.0, (
        f"130-page estimate must be < $2.00, got ${estimate.total_usd}"
    )

    # Verify basis
    assert estimate.basis == "pages"

    # Verify element_count calculation: int(130 * 1.6) = 208
    expected_element_count = int(130 * 1.6)
    assert estimate.element_count == expected_element_count


def test_task_runs_caps_at_40():
    """Spec: task_runs caps at settings.max_task_runs (40)."""
    counts = {ElementCategory.REAL_PERSON: 250}
    page_count = 130

    estimate = estimate_cost(counts, page_count)

    # Without cap: ceil(250 * 1.0) = 250
    # With cap: min(250, 40) = 40
    assert estimate.task_runs == 40


def test_basis_field_elements():
    """basis field is 'elements' for estimate_cost."""
    counts = {ElementCategory.CHARACTER_NAME: 1}
    estimate = estimate_cost(counts, 1)
    assert estimate.basis == "elements"


def test_basis_field_pages():
    """basis field is 'pages' for estimate_from_pages."""
    estimate = estimate_from_pages(10)
    assert estimate.basis == "pages"


def test_determinism_estimate_cost():
    """Two calls to estimate_cost with same inputs produce identical results."""
    counts = {
        ElementCategory.CHARACTER_NAME: 20,
        ElementCategory.BUSINESS_ORG: 5,
    }
    page_count = 50

    estimate1 = estimate_cost(counts, page_count)
    estimate2 = estimate_cost(counts, page_count)

    assert estimate1 == estimate2


def test_determinism_estimate_from_pages():
    """Two calls to estimate_from_pages with same input produce identical results."""
    estimate1 = estimate_from_pages(50)
    estimate2 = estimate_from_pages(50)

    assert estimate1 == estimate2


def test_estimate_cost_with_all_categories():
    """estimate_cost works with all 9 element categories."""
    counts = {
        ElementCategory.CHARACTER_NAME: 10,
        ElementCategory.BUSINESS_ORG: 5,
        ElementCategory.LOCATION_ADDRESS: 8,
        ElementCategory.PHONE_URL_EMAIL: 3,
        ElementCategory.PRODUCT_BRAND: 4,
        ElementCategory.REFERENCED_WORK: 2,
        ElementCategory.REAL_PERSON: 1,
        ElementCategory.ON_SCREEN_TEXT: 15,
        ElementCategory.VEHICLE_IDENTIFIER: 2,
    }
    page_count = 50

    estimate = estimate_cost(counts, page_count)

    assert estimate.element_count == 50
    assert estimate.basis == "elements"
    # Verify basic structure
    assert estimate.search_requests > 0
    assert estimate.task_runs > 0
    assert estimate.total_usd > 0
    assert estimate.gemini_usd > 0
    assert estimate.parallel_usd > 0


def test_estimate_from_pages_element_count_calculation():
    """Element count from pages calculated as int(page_count * 1.6)."""
    for page_count in [10, 50, 100, 130]:
        estimate = estimate_from_pages(page_count)
        expected_element_count = int(page_count * 1.6)
        assert estimate.element_count == expected_element_count
