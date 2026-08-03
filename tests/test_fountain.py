"""Tests for Fountain screenplay parser."""
from pathlib import Path

import pytest

from clearslate.parsing.fountain import parse_fountain


@pytest.fixture
def mini_fountain_text() -> str:
    """Load the mini script fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "mini_script.fountain"
    return fixture_path.read_text()


def test_page_count(mini_fountain_text: str) -> None:
    """Test that 120 post-title lines produce 3 pages (55/55/10)."""
    result = parse_fountain(mini_fountain_text)
    assert result.page_count == 3
    assert len(result.pages) == 3


def test_title_page_stripped(mini_fountain_text: str) -> None:
    """Test that title page is not in page 1, and INT. KITCHEN - DAY appears."""
    result = parse_fountain(mini_fountain_text)
    page1_text = result.pages[0].text

    # Title page should not appear in page 1
    assert "Title: ClearSlate Test" not in page1_text
    assert "Author: Test Writer" not in page1_text

    # First line should be INT. KITCHEN - DAY
    assert "INT. KITCHEN - DAY" in page1_text
    lines = page1_text.split("\n")
    assert lines[0] == "INT. KITCHEN - DAY"


def test_scene_headings_map(mini_fountain_text: str) -> None:
    """Test that scene headings are correctly mapped to pages."""
    result = parse_fountain(mini_fountain_text)

    # Should have at least 2 scene headings
    assert len(result.scene_headings) >= 2

    # First scene heading: INT. KITCHEN - DAY on page 1
    assert (1, "INT. KITCHEN - DAY") in result.scene_headings

    # Second scene heading: EXT. PARKING LOT - NIGHT on page 2
    assert (2, "EXT. PARKING LOT - NIGHT") in result.scene_headings


def test_source_format(mini_fountain_text: str) -> None:
    """Test that source_format is set to 'fountain'."""
    result = parse_fountain(mini_fountain_text)
    assert result.source_format == "fountain"


def test_pages_are_1_indexed(mini_fountain_text: str) -> None:
    """Test that page numbers are 1-indexed."""
    result = parse_fountain(mini_fountain_text)
    page_numbers = [p.page for p in result.pages]
    assert page_numbers == [1, 2, 3]


def test_page_1_has_55_lines(mini_fountain_text: str) -> None:
    """Test that page 1 has exactly 55 lines."""
    result = parse_fountain(mini_fountain_text)
    page1_lines = result.pages[0].text.split("\n")
    assert len(page1_lines) == 55


def test_page_2_has_55_lines(mini_fountain_text: str) -> None:
    """Test that page 2 has exactly 55 lines."""
    result = parse_fountain(mini_fountain_text)
    page2_lines = result.pages[1].text.split("\n")
    assert len(page2_lines) == 55


def test_page_3_has_10_lines(mini_fountain_text: str) -> None:
    """Test that page 3 has exactly 10 lines (remaining)."""
    result = parse_fountain(mini_fountain_text)
    page3_lines = result.pages[2].text.split("\n")
    assert len(page3_lines) == 10
