"""Fountain screenplay format parser."""
import re

from clearslate.models import PageText, ParsedScript

LINES_PER_PAGE = 55


def _is_title_page_key_value(line: str) -> bool:
    """Check if line matches title page key-value pattern: ^[A-Za-z][A-Za-z ]*:"""
    return bool(re.match(r"^[A-Za-z][A-Za-z ]*:", line))


def _is_indented(line: str) -> bool:
    """Check if line starts with whitespace (space or tab)."""
    return len(line) > 0 and line[0] in (" ", "\t")


def _strip_title_page(text: str) -> str:
    """
    Strip title page from Fountain text.

    Title page is detected if first non-empty line matches ^[A-Za-z][A-Za-z ]*:
    It ends at the first blank line followed by content that is:
    - NOT indented
    - NOT matching the key-value pattern

    Returns the text with title page removed.
    """
    lines = text.split("\n")

    # Check if first non-empty line matches title page pattern
    first_non_empty_idx = None
    for i, line in enumerate(lines):
        if line.strip():
            first_non_empty_idx = i
            break

    # If no non-empty line, or first non-empty line doesn't match pattern, no title page
    if first_non_empty_idx is None or not _is_title_page_key_value(lines[first_non_empty_idx]):
        return text

    # Find the end of title page: first blank line followed by non-title-page content
    for i in range(first_non_empty_idx, len(lines) - 1):
        if lines[i].strip() == "":  # Found a blank line
            # Check the next non-blank line
            next_non_blank_idx = None
            for j in range(i + 1, len(lines)):
                if lines[j].strip():
                    next_non_blank_idx = j
                    break

            # If we found a next non-blank line
            if next_non_blank_idx is not None:
                next_line = lines[next_non_blank_idx]
                # If it's NOT indented and NOT key-value, title page ends here
                if not _is_indented(next_line) and not _is_title_page_key_value(next_line):
                    # Return everything after this blank line
                    return "\n".join(lines[i + 1 :])

    # No title page boundary found, return as-is
    return text


def _is_scene_heading(line: str) -> bool:
    r"""
    Check if line is a scene heading.

    Matches:
    - ^(?:INT|EXT|EST|INT\.?/EXT|I/E)[.\s] (case-insensitive)
    - OR ^\.[A-Za-z] (forced heading starting with dot)
    """
    stripped = line.strip()

    # Check forced heading pattern (leading dot)
    if re.match(r"^\.[A-Za-z]", stripped):
        return True

    # Check standard scene heading pattern
    return bool(re.match(r"^(?:INT|EXT|EST|INT\.?/EXT|I/E)[.\s]", stripped, re.IGNORECASE))


def _get_heading_text(line: str) -> str:
    """
    Extract heading text from line.
    For forced headings (starting with dot), remove the leading dot.
    """
    stripped = line.strip()

    # If forced heading, remove leading dot
    if re.match(r"^\.[A-Za-z]", stripped):
        return stripped[1:]

    return stripped


def parse_fountain(text: str) -> ParsedScript:
    """
    Parse Fountain screenplay format.

    Args:
        text: Raw Fountain screenplay text

    Returns:
        ParsedScript with pages, page_count, and scene_headings
    """
    # Strip title page
    content = _strip_title_page(text)

    # Split into lines
    lines = content.split("\n")

    # Paginate at LINES_PER_PAGE
    pages: list[PageText] = []
    scene_headings: list[tuple[int, str]] = []

    for page_idx in range(0, len(lines), LINES_PER_PAGE):
        page_lines = lines[page_idx : page_idx + LINES_PER_PAGE]
        page_text = "\n".join(page_lines)
        page_number = (page_idx // LINES_PER_PAGE) + 1  # 1-indexed

        pages.append(PageText(page=page_number, text=page_text))

        # Find scene headings in this page
        for line in page_lines:
            if _is_scene_heading(line):
                heading_text = _get_heading_text(line)
                scene_headings.append((page_number, heading_text))

    return ParsedScript(
        source_format="fountain",
        pages=pages,
        page_count=len(pages),
        scene_headings=scene_headings,
    )
