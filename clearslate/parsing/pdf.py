"""PDF screenplay parser."""
import io
import re

import pdfplumber

from clearslate.errors import ParserError
from clearslate.models import PageText, ParsedScript

LOW_TEXT_CHARS = 40
LOW_TEXT_PAGE_RATIO = 0.30

# Scene heading regex - reuse the same pattern as fountain
SCENE_HEADING_PATTERN = re.compile(
    r"^(?:INT|EXT|EST|INT\.?/EXT|I/E)[.\s]", re.IGNORECASE
)


def _is_scene_heading(line: str) -> bool:
    """Check if line is a scene heading."""
    stripped = line.strip()

    # Check forced heading pattern (leading dot)
    if re.match(r"^\.[A-Za-z]", stripped):
        return True

    # Check standard scene heading pattern
    return bool(SCENE_HEADING_PATTERN.match(stripped))


def _get_heading_text(line: str) -> str:
    """Extract heading text from line."""
    stripped = line.strip()

    # If forced heading, remove leading dot
    if re.match(r"^\.[A-Za-z]", stripped):
        return stripped[1:]

    return stripped


def parse_pdf(content: bytes) -> ParsedScript:
    """
    Parse PDF screenplay.

    Args:
        content: Raw PDF bytes

    Returns:
        ParsedScript with pages, page_count, and scene_headings

    Raises:
        ParserError: If PDF is low-text, empty, or otherwise invalid
    """
    try:
        pdf = pdfplumber.open(io.BytesIO(content))
    except Exception as e:
        raise ParserError("low_text_pdf", "This PDF appears to be scanned or has little extractable text — try pasting the text instead.") from e

    # Check if PDF is empty
    if len(pdf.pages) == 0:
        raise ParserError("low_text_pdf", "This PDF appears to be scanned or has little extractable text — try pasting the text instead.")

    # Extract text from each page and check low-text ratio
    pages: list[PageText] = []
    low_text_count = 0

    for page_num, page in enumerate(pdf.pages, start=1):
        text = page.extract_text() or ""
        pages.append(PageText(page=page_num, text=text))

        # Check if page has low text
        if len(text.strip()) < LOW_TEXT_CHARS:
            low_text_count += 1

    # Check low-text ratio
    if len(pages) > 0:
        low_text_ratio = low_text_count / len(pages)
        if low_text_ratio > LOW_TEXT_PAGE_RATIO:
            raise ParserError("low_text_pdf", "This PDF appears to be scanned or has little extractable text — try pasting the text instead.")

    # Extract scene headings
    scene_headings: list[tuple[int, str]] = []
    for page in pages:
        lines = page.text.split("\n")
        for line in lines:
            if _is_scene_heading(line):
                heading_text = _get_heading_text(line)
                scene_headings.append((page.page, heading_text))

    pdf.close()

    return ParsedScript(
        source_format="pdf",
        pages=pages,
        page_count=len(pages),
        scene_headings=scene_headings,
    )
