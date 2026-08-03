"""Tests for upload router."""
from pathlib import Path

import pytest

from clearslate.errors import ParserError
from clearslate.parsing.router import parse_upload


@pytest.fixture
def two_page_pdf_bytes() -> bytes:
    """Load the two-page PDF fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "two_page.pdf"
    return fixture_path.read_bytes()


def test_pdf_file_routes_to_pdf_parser(two_page_pdf_bytes: bytes) -> None:
    """Test that .pdf filename routes to parse_pdf."""
    result = parse_upload(filename="test.pdf", content=two_page_pdf_bytes)
    assert result.source_format == "pdf"
    assert result.page_count == 2


def test_fountain_paste_routes_to_fountain_parser() -> None:
    """Test that pasted Fountain text routes to parse_fountain."""
    fountain_text = """Title: Test Script
Author: Test

INT. KITCHEN - DAY
This is a kitchen scene.

EXT. PARK - DAY
This is a park scene.
"""
    # Repeat to ensure multiple pages
    pasted_text = fountain_text + "\nSome line\n" * 500

    result = parse_upload(pasted_text=pasted_text)
    assert result.source_format == "fountain"
    assert result.page_count > 1


def test_prose_paste_formats_as_text() -> None:
    """Test that pasted prose without scene headings formats as text."""
    prose_text = "This is just regular prose.\n" * 60  # Enough for multiple pages

    result = parse_upload(pasted_text=prose_text)
    assert result.source_format == "text"


def test_no_args_raises_empty_input() -> None:
    """Test that no arguments raises empty_input error."""
    with pytest.raises(ParserError) as exc_info:
        parse_upload()

    assert exc_info.value.code == "empty_input"
    assert "Provide a script file or pasted text" in exc_info.value.message


def test_131_page_paste_raises_too_long() -> None:
    """Test that exceeding 130 page limit raises too_long error."""
    # Create text that will result in > 130 pages
    # 131 pages = 131 * 55 = 7205 lines, but splitting adds empty string so we need to
    # account for that
    long_text = "line\n" * (131 * 55)

    with pytest.raises(ParserError) as exc_info:
        parse_upload(pasted_text=long_text)

    assert exc_info.value.code == "too_long"
    assert "130" in exc_info.value.message


def test_invalid_utf8_raises_bad_encoding() -> None:
    """Test that invalid UTF-8 bytes raise bad_encoding error."""
    # Create invalid UTF-8 bytes
    invalid_bytes = b"\x80\x81\x82\x83"

    with pytest.raises(ParserError) as exc_info:
        parse_upload(filename="test.txt", content=invalid_bytes)

    assert exc_info.value.code == "bad_encoding"
    assert "UTF-8" in exc_info.value.message


def test_fountain_file_extension_routes_to_fountain() -> None:
    """Test that .fountain file extension routes to fountain parser."""
    fountain_text = """Title: Test
Author: Test

INT. BEDROOM - NIGHT
Some bedroom scene.
"""
    pasted_text = fountain_text + "\nLine\n" * 300

    result = parse_upload(filename="test.fountain", content=pasted_text.encode("utf-8"))
    assert result.source_format == "fountain"


def test_txt_file_extension_sniffs_format() -> None:
    """Test that .txt file extension sniffs the format."""
    prose_text = "This is regular prose without any scene headings.\n" * 60

    result = parse_upload(filename="test.txt", content=prose_text.encode("utf-8"))
    assert result.source_format == "text"


def test_unknown_extension_treats_as_text() -> None:
    """Test that unknown file extension is treated as text."""
    prose_text = "This is regular prose.\n" * 60

    result = parse_upload(filename="test.unknown", content=prose_text.encode("utf-8"))
    assert result.source_format == "text"
