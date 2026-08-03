"""Upload router - routes uploaded files or pasted text to appropriate parser."""
import re

from clearslate.config import settings
from clearslate.errors import ParserError
from clearslate.models import ParsedScript
from clearslate.parsing.fountain import parse_fountain
from clearslate.parsing.pdf import parse_pdf

# Scene heading regex for sniffing
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


def _sniff_format(text: str) -> str:
    """
    Sniff the format of text content.

    Returns "fountain" if scene heading regex matches in first 100 lines.
    Otherwise returns "text".
    """
    lines = text.split("\n")
    for i, line in enumerate(lines[:100]):
        if _is_scene_heading(line):
            return "fountain"

    return "text"


def _parse_plain_text(text: str) -> ParsedScript:
    """
    Parse plain text screenplay.

    Paginate at 55 lines per page, no title page stripping.
    """
    from clearslate.parsing.fountain import LINES_PER_PAGE

    lines = text.split("\n")
    pages = []

    for page_idx in range(0, len(lines), LINES_PER_PAGE):
        page_lines = lines[page_idx : page_idx + LINES_PER_PAGE]
        page_text = "\n".join(page_lines)
        page_number = (page_idx // LINES_PER_PAGE) + 1  # 1-indexed

        pages.append(__import__("clearslate.models", fromlist=["PageText"]).PageText(page=page_number, text=page_text))

    return ParsedScript(
        source_format="text",
        pages=pages,
        page_count=len(pages),
        scene_headings=[],
    )


def parse_upload(
    *,
    filename: str | None = None,
    content: bytes | None = None,
    pasted_text: str | None = None,
) -> ParsedScript:
    """
    Route uploaded file or pasted text to appropriate parser.

    Args:
        filename: Original filename (optional)
        content: File content as bytes (optional)
        pasted_text: Text pasted directly (optional)

    Returns:
        ParsedScript

    Raises:
        ParserError: If input is invalid, empty, too long, etc.
    """
    # Check if we have any input
    if not (content or pasted_text):
        raise ParserError("empty_input", "Provide a script file or pasted text.")

    # Handle PDF files
    if filename and filename.lower().endswith(".pdf"):
        if not content:
            raise ParserError("empty_input", "Provide a script file or pasted text.")
        result = parse_pdf(content)
        if result.page_count > settings.max_pages:
            raise ParserError(
                "too_long",
                f"Script is {result.page_count} pages; the limit is {settings.max_pages}.",
            )
        return result

    # Handle text-based inputs (file or pasted)
    text_content = None

    if pasted_text:
        text_content = pasted_text
    elif content:
        # Decode content as UTF-8
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ParserError("bad_encoding", "File is not valid UTF-8 text.") from e

    if text_content is None:
        raise ParserError("empty_input", "Provide a script file or pasted text.")

    # Sniff format for unknown extensions or pasted text
    if filename:
        # .fountain or .txt extension can still require sniffing (for .txt)
        if filename.lower().endswith(".fountain"):
            format_type = "fountain"
        else:
            # For .txt and unknown extensions, sniff
            format_type = _sniff_format(text_content)
    else:
        # No filename provided (pasted text), sniff
        format_type = _sniff_format(text_content)

    # Parse based on detected format
    if format_type == "fountain":
        result = parse_fountain(text_content)
    else:  # "text"
        result = _parse_plain_text(text_content)

    # Check page count limit AFTER parsing
    if result.page_count > settings.max_pages:
        raise ParserError(
            "too_long",
            f"Script is {result.page_count} pages; the limit is {settings.max_pages}.",
        )

    return result
