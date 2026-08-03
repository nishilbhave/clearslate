"""
Tests for core Pydantic models.
"""
from clearslate.models import (
    Element,
    ElementCategory,
    ElementStatus,
    RunState,
)


def test_element_round_trip_with_defaults():
    """Element round-trip with defaults: status==pending, findings==[], grade is None."""
    elem = Element(
        id="test-1",
        category=ElementCategory.CHARACTER_NAME,
        text="John Doe",
        normalized_text="john doe",
        pages=[1, 2],
        context_snippet="The character John Doe appears in the scene.",
    )

    # Check defaults
    assert elem.status == ElementStatus.PENDING
    assert elem.findings == []
    assert elem.grade is None
    assert elem.scene is None
    assert elem.rule_citation is None
    assert elem.alternatives == []

    # Check round-trip
    data = elem.model_dump()
    elem2 = Element(**data)
    assert elem2.status == ElementStatus.PENDING
    assert elem2.findings == []
    assert elem2.grade is None


def test_element_category_has_exactly_9_members():
    """ElementCategory enum has exactly 9 categories."""
    categories = [c for c in ElementCategory]
    assert len(categories) == 9

    # Verify all expected categories are present
    expected = {
        ElementCategory.CHARACTER_NAME,
        ElementCategory.BUSINESS_ORG,
        ElementCategory.LOCATION_ADDRESS,
        ElementCategory.PHONE_URL_EMAIL,
        ElementCategory.PRODUCT_BRAND,
        ElementCategory.REFERENCED_WORK,
        ElementCategory.REAL_PERSON,
        ElementCategory.ON_SCREEN_TEXT,
        ElementCategory.VEHICLE_IDENTIFIER,
    }
    assert set(categories) == expected


def test_run_state_has_all_spec_states():
    """RunState enum contains all 7+ spec states."""
    states = [s for s in RunState]

    # Verify all expected states are present
    expected_states = {
        "PENDING",
        "BREAKDOWN",
        "AWAITING_START",
        "RESEARCH",
        "GRADING",
        "REPORT",
        "DONE",
        "FAILED",
    }

    actual_state_names = {s.name for s in states}
    assert expected_states.issubset(actual_state_names), (
        f"RunState missing states: {expected_states - actual_state_names}"
    )
