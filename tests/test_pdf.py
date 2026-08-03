"""Tests for PDF parser."""
from pathlib import Path

import pytest

from clearslate.errors import ParserError
from clearslate.parsing.pdf import parse_pdf


@pytest.fixture
def two_page_pdf_bytes() -> bytes:
    """Load the two-page PDF fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "two_page.pdf"
    return fixture_path.read_bytes()


def test_two_page_pdf_extracts_pages(two_page_pdf_bytes: bytes) -> None:
    """Test that two-page PDF is parsed with 2 pages."""
    result = parse_pdf(two_page_pdf_bytes)
    assert result.page_count == 2
    assert len(result.pages) == 2


def test_two_page_pdf_source_format(two_page_pdf_bytes: bytes) -> None:
    """Test that source_format is 'pdf'."""
    result = parse_pdf(two_page_pdf_bytes)
    assert result.source_format == "pdf"


def test_two_page_pdf_page_markers(two_page_pdf_bytes: bytes) -> None:
    """Test that page markers appear in correct pages."""
    result = parse_pdf(two_page_pdf_bytes)

    # First page should have PAGE-ONE-MARKER
    assert "PAGE-ONE-MARKER" in result.pages[0].text

    # Second page should have PAGE-TWO-MARKER
    assert "PAGE-TWO-MARKER" in result.pages[1].text


def test_two_page_pdf_page_numbers_are_1_indexed(two_page_pdf_bytes: bytes) -> None:
    """Test that page numbers are 1-indexed."""
    result = parse_pdf(two_page_pdf_bytes)
    page_numbers = [p.page for p in result.pages]
    assert page_numbers == [1, 2]


def test_empty_pdf_raises_low_text_pdf() -> None:
    """Test that a PDF with no pages raises low_text_pdf error."""
    # Create a minimal PDF with a single empty page using fpdf2
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    # Don't add any text - just an empty page
    pdf_bytes = pdf.output()

    with pytest.raises(ParserError) as exc_info:
        parse_pdf(pdf_bytes)

    assert exc_info.value.code == "low_text_pdf"
    assert "little extractable text" in exc_info.value.message
