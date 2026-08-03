"""
Page chunker for breaking large scripts into overlapping chunks for processing.

Chunks are created with a stride (chunk_size - overlap) such that:
- Chunks start at indices 0, stride, 2*stride, ...
- Each chunk covers up to chunk_size pages
- The final chunk may be shorter but is never empty
- No redundant trailing chunks (fully contained in a previous chunk)
"""
from pydantic import BaseModel

from clearslate.models import PageText


class Chunk(BaseModel):
    """
    A contiguous chunk of pages from a script.

    Attributes:
        index: 0-based chunk ordinal (first chunk is 0, second is 1, etc.)
        start_page: 1-indexed absolute page number of first page in chunk
        end_page: 1-indexed absolute page number of last page in chunk
        text: Joined page text with [PAGE n] markers for each page
    """

    index: int
    start_page: int
    end_page: int
    text: str


def chunk_pages(
    pages: list[PageText], *, chunk_size: int = 12, overlap: int = 2
) -> list[Chunk]:
    """
    Break a list of pages into overlapping chunks.

    Args:
        pages: List of PageText objects (page field is 1-indexed)
        chunk_size: Number of pages per chunk (default 12)
        overlap: Number of pages to overlap between chunks (default 2)

    Returns:
        List of Chunk objects with no redundant trailing chunks.

    Example:
        With 130 pages, chunk_size=12, overlap=2 (stride=10):
        - Chunk 0: pages 1-12
        - Chunk 1: pages 11-22
        - Chunk 2: pages 21-32
        - ...
        - Chunk 12: pages 121-130
        Total: 13 chunks
    """
    if not pages:
        return []

    stride = chunk_size - overlap
    chunks: list[Chunk] = []
    prev_end_idx = 0

    # Iterate through start indices: 0, stride, 2*stride, ...
    for chunk_idx, start_idx in enumerate(range(0, len(pages), stride)):
        end_idx = min(start_idx + chunk_size, len(pages))

        # Only create chunk if it contains new content not in previous chunk
        if end_idx <= prev_end_idx:
            break

        # Build chunk text: [PAGE n]\ntext for each page, joined by \n
        chunk_lines = []
        for page_obj in pages[start_idx:end_idx]:
            chunk_lines.append(f"[PAGE {page_obj.page}]")
            chunk_lines.append(page_obj.text)

        chunk_text = "\n".join(chunk_lines)

        # start_page and end_page are 1-indexed absolute page numbers
        start_page = pages[start_idx].page
        end_page = pages[end_idx - 1].page

        chunk = Chunk(
            index=chunk_idx,
            start_page=start_page,
            end_page=end_page,
            text=chunk_text,
        )
        chunks.append(chunk)
        prev_end_idx = end_idx

    return chunks


def build_chunk_prompt(chunk: Chunk) -> str:
    """
    Build a deterministic prompt for extracting clearance elements from a chunk.

    Args:
        chunk: A Chunk object

    Returns:
        A formatted prompt string with exact format:
        "Extract all clearance elements from this screenplay excerpt covering
         pages {start}-{end}. Cite page numbers ONLY from the [PAGE n] markers.\n\n{text}"
    """
    return (
        f"Extract all clearance elements from this screenplay excerpt "
        f"covering pages {chunk.start_page}-{chunk.end_page}. "
        f"Cite page numbers ONLY from the [PAGE n] markers.\n\n{chunk.text}"
    )
