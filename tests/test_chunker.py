"""
Tests for the page chunker (TDD).
"""
from clearslate.breakdown.chunker import Chunk, build_chunk_prompt, chunk_pages
from clearslate.models import PageText


def make_pages(n: int) -> list[PageText]:
    """Helper to fabricate pages 1..n with dummy text."""
    return [PageText(page=i, text=f"page {i} body") for i in range(1, n + 1)]


class TestChunkPages:
    """Test chunk_pages() function."""

    def test_130_pages_produces_13_chunks(self):
        """130 pages with stride 10 should produce exactly 13 chunks."""
        pages = make_pages(130)
        chunks = chunk_pages(pages, chunk_size=12, overlap=2)
        assert len(chunks) == 13

    def test_130_pages_chunks_correct_ordinal_indices(self):
        """Verify chunks have correct ordinal indices 0, 1, 2, ..., 12."""
        pages = make_pages(130)
        chunks = chunk_pages(pages, chunk_size=12, overlap=2)
        for i, chunk in enumerate(chunks):
            assert chunk.index == i

    def test_130_pages_chunk_1_bounds(self):
        """chunks[1].start_page == 11 and chunks[1].end_page == 22."""
        pages = make_pages(130)
        chunks = chunk_pages(pages, chunk_size=12, overlap=2)
        assert chunks[1].start_page == 11
        assert chunks[1].end_page == 22

    def test_130_pages_last_chunk_ends_at_130(self):
        """Last chunk should end at page 130."""
        pages = make_pages(130)
        chunks = chunk_pages(pages, chunk_size=12, overlap=2)
        assert chunks[-1].end_page == 130

    def test_7_pages_produces_1_chunk(self):
        """7 pages should produce exactly 1 chunk."""
        pages = make_pages(7)
        chunks = chunk_pages(pages, chunk_size=12, overlap=2)
        assert len(chunks) == 1
        assert chunks[0].start_page == 1
        assert chunks[0].end_page == 7

    def test_12_pages_produces_1_chunk(self):
        """12 pages (exactly chunk_size) should produce exactly 1 chunk, not 2."""
        pages = make_pages(12)
        chunks = chunk_pages(pages, chunk_size=12, overlap=2)
        assert len(chunks) == 1
        assert chunks[0].start_page == 1
        assert chunks[0].end_page == 12

    def test_chunk_index_is_0_based(self):
        """Chunk.index should be 0-based."""
        pages = make_pages(130)
        chunks = chunk_pages(pages, chunk_size=12, overlap=2)
        assert chunks[0].index == 0
        assert chunks[1].index == 1
        assert chunks[12].index == 12

    def test_chunk_pages_are_1_indexed(self):
        """start_page and end_page should be 1-indexed absolute page numbers."""
        pages = make_pages(30)
        chunks = chunk_pages(pages, chunk_size=12, overlap=2)
        assert chunks[0].start_page == 1
        assert chunks[0].end_page == 12
        assert chunks[1].start_page == 11
        assert chunks[1].end_page == 22
        assert chunks[2].start_page == 21
        assert chunks[2].end_page == 30

    def test_chunk_text_contains_page_markers(self):
        """Each chunk's text should contain [PAGE n] markers for its pages."""
        pages = make_pages(25)
        chunks = chunk_pages(pages, chunk_size=12, overlap=2)

        # First chunk should have pages 1-12
        chunk_0_text = chunks[0].text
        for page_num in range(1, 13):
            assert f"[PAGE {page_num}]" in chunk_0_text

        # Second chunk should have pages 11-22
        chunk_1_text = chunks[1].text
        for page_num in range(11, 23):
            assert f"[PAGE {page_num}]" in chunk_1_text

    def test_chunk_text_contains_only_own_page_markers(self):
        """Each chunk should contain ONLY [PAGE n] markers for its own pages."""
        pages = make_pages(25)
        chunks = chunk_pages(pages, chunk_size=12, overlap=2)

        # First chunk (pages 1-12) should not have markers for pages 13+
        chunk_0_text = chunks[0].text
        for page_num in range(13, 26):
            assert f"[PAGE {page_num}]" not in chunk_0_text

        # Second chunk (pages 11-22) should not have markers for pages 1-10 or 23+
        chunk_1_text = chunks[1].text
        for page_num in range(1, 11):
            assert f"[PAGE {page_num}]" not in chunk_1_text
        for page_num in range(23, 26):
            assert f"[PAGE {page_num}]" not in chunk_1_text

    def test_chunk_text_format(self):
        """Chunk text should be formatted as [PAGE n]\\npage text for each page."""
        pages = make_pages(5)
        chunks = chunk_pages(pages, chunk_size=12, overlap=2)
        chunk = chunks[0]

        expected_lines = [
            "[PAGE 1]",
            "page 1 body",
            "[PAGE 2]",
            "page 2 body",
            "[PAGE 3]",
            "page 3 body",
            "[PAGE 4]",
            "page 4 body",
            "[PAGE 5]",
            "page 5 body",
        ]
        expected_text = "\n".join(expected_lines)
        assert chunk.text == expected_text

    def test_chunk_never_empty(self):
        """Each chunk should never be empty."""
        pages = make_pages(130)
        chunks = chunk_pages(pages, chunk_size=12, overlap=2)
        for chunk in chunks:
            assert chunk.text
            assert chunk.start_page <= chunk.end_page
            assert len(chunk.text) > 0


class TestBuildChunkPrompt:
    """Test build_chunk_prompt() function."""

    def test_prompt_format(self):
        """Prompt should follow exact format specification."""
        chunk = Chunk(
            index=0,
            start_page=1,
            end_page=12,
            text="[PAGE 1]\npage 1 body\n[PAGE 2]\npage 2 body",
        )
        prompt = build_chunk_prompt(chunk)
        expected = (
            "Extract all clearance elements from this screenplay excerpt "
            "covering pages 1-12. Cite page numbers ONLY from the [PAGE n] markers.\n\n"
            "[PAGE 1]\npage 1 body\n[PAGE 2]\npage 2 body"
        )
        assert prompt == expected

    def test_prompt_deterministic(self):
        """Same chunk should produce byte-identical prompt."""
        chunk = Chunk(
            index=1,
            start_page=11,
            end_page=22,
            text="[PAGE 11]\npage 11 body\n[PAGE 12]\npage 12 body",
        )
        prompt1 = build_chunk_prompt(chunk)
        prompt2 = build_chunk_prompt(chunk)
        assert prompt1 == prompt2
        assert prompt1.encode() == prompt2.encode()

    def test_prompt_different_for_different_pages(self):
        """Different chunks should produce different prompts."""
        chunk1 = Chunk(
            index=0,
            start_page=1,
            end_page=12,
            text="[PAGE 1]\npage 1",
        )
        chunk2 = Chunk(
            index=1,
            start_page=11,
            end_page=22,
            text="[PAGE 11]\npage 11",
        )
        prompt1 = build_chunk_prompt(chunk1)
        prompt2 = build_chunk_prompt(chunk2)
        assert prompt1 != prompt2

    def test_prompt_includes_page_range(self):
        """Prompt should include the page range in the message."""
        chunk = Chunk(
            index=2,
            start_page=21,
            end_page=32,
            text="some text",
        )
        prompt = build_chunk_prompt(chunk)
        assert "21-32" in prompt

    def test_prompt_includes_chunk_text(self):
        """Prompt should include the full chunk text."""
        text = "[PAGE 5]\npage 5 body\n[PAGE 6]\npage 6 body"
        chunk = Chunk(index=0, start_page=5, end_page=6, text=text)
        prompt = build_chunk_prompt(chunk)
        assert text in prompt
