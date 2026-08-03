"""Tests for the breakdown stage: validate → one feedback retry → hard-fail; assembly."""
import json

import pytest

from clearslate.agents.invoker import QueuedInvoker
from clearslate.breakdown.chunker import chunk_pages
from clearslate.breakdown.stage import BreakdownResult, extract_chunk, run_breakdown
from clearslate.errors import BreakdownStageError, ExtractionValidationError
from clearslate.models import ElementStatus, PageText, ParsedScript


def make_pages(n: int) -> list[PageText]:
    """Helper to fabricate pages 1..n with dummy text."""
    return [PageText(page=i, text=f"page {i} body") for i in range(1, n + 1)]


def make_parsed(n: int) -> ParsedScript:
    return ParsedScript(source_format="text", pages=make_pages(n), page_count=n)


def extraction_json(elements: list[dict]) -> str:
    """Build a valid ChunkExtraction JSON string from a list of element dicts."""
    return json.dumps({"elements": elements})


def element_dict(
    category: str = "character_name",
    text: str = "Alice",
    pages: list[int] | None = None,
    scene: str | None = None,
    context_snippet: str = "Alice enters the room",
) -> dict:
    return {
        "category": category,
        "text": text,
        "pages": pages if pages is not None else [1],
        "scene": scene,
        "context_snippet": context_snippet,
    }


class TestHappyPath:
    async def test_single_chunk_two_elements(self):
        parsed = make_parsed(7)
        response = extraction_json(
            [
                element_dict(category="character_name", text="Alice", pages=[1]),
                element_dict(category="business_org", text="Acme Corp", pages=[2]),
            ]
        )
        invoker = QueuedInvoker([response])

        result = await run_breakdown(parsed, invoker, concurrency=1)

        assert isinstance(result, BreakdownResult)
        assert result.chunk_count == 1
        assert result.retried_chunks == []
        assert len(result.elements) == 2
        ids = sorted(e.id for e in result.elements)
        assert ids == ["el_0001", "el_0002"]
        for element in result.elements:
            assert element.status == ElementStatus.PENDING
            assert element.normalized_text  # filled by dedupe/normalize
        assert len(invoker.prompts) == 1


class TestRetryPath:
    async def test_bad_enum_then_valid_retries_once(self):
        parsed = make_parsed(7)
        bad_response = extraction_json([element_dict(category="villain", text="Bob", pages=[1])])
        good_response = extraction_json([element_dict(category="character_name", text="Bob", pages=[1])])
        invoker = QueuedInvoker([bad_response, good_response])

        result = await run_breakdown(parsed, invoker, concurrency=1)

        assert len(invoker.prompts) == 2
        assert "failed validation" in invoker.prompts[1]
        assert result.retried_chunks == [0]
        assert len(result.elements) == 1
        assert result.elements[0].text == "Bob"

    async def test_extract_chunk_retries_once_directly(self):
        chunks = chunk_pages(make_pages(7), chunk_size=12, overlap=2)
        chunk = chunks[0]
        bad_response = "not json at all"
        good_response = extraction_json([element_dict(category="character_name", text="Bob", pages=[1])])
        invoker = QueuedInvoker([bad_response, good_response])

        extraction = await extract_chunk(invoker, chunk)

        assert len(invoker.prompts) == 2
        assert "failed validation" in invoker.prompts[1]
        assert len(extraction.elements) == 1
        assert extraction.elements[0].text == "Bob"


class TestHardFail:
    async def test_extract_chunk_raises_after_two_invalid(self):
        chunks = chunk_pages(make_pages(7), chunk_size=12, overlap=2)
        chunk = chunks[0]
        invoker = QueuedInvoker(["not json", "still not json"])

        with pytest.raises(ExtractionValidationError) as exc_info:
            await extract_chunk(invoker, chunk)

        assert exc_info.value.code == "invalid_llm_output"
        assert str(chunk.index) in exc_info.value.message
        assert len(invoker.prompts) == 2

    async def test_run_breakdown_raises_breakdown_stage_error_naming_chunk(self):
        parsed = make_parsed(7)
        invoker = QueuedInvoker(["not json", "still not json"])

        with pytest.raises(BreakdownStageError) as exc_info:
            await run_breakdown(parsed, invoker, concurrency=1)

        assert exc_info.value.code == "chunks_failed"
        assert "0" in exc_info.value.message


class TestPageBoundsViolation:
    async def test_out_of_range_page_triggers_retry(self):
        parsed = make_parsed(7)  # single chunk covering pages 1-7
        bad_response = extraction_json(
            [element_dict(category="character_name", text="Carl", pages=[99])]
        )
        good_response = extraction_json(
            [element_dict(category="character_name", text="Carl", pages=[3])]
        )
        invoker = QueuedInvoker([bad_response, good_response])

        result = await run_breakdown(parsed, invoker, concurrency=1)

        assert len(invoker.prompts) == 2
        assert "failed validation" in invoker.prompts[1]
        assert result.retried_chunks == [0]
        assert result.elements[0].pages == [3]

    async def test_empty_pages_triggers_retry(self):
        parsed = make_parsed(7)
        bad_response = extraction_json(
            [element_dict(category="character_name", text="Carl", pages=[])]
        )
        good_response = extraction_json(
            [element_dict(category="character_name", text="Carl", pages=[4])]
        )
        invoker = QueuedInvoker([bad_response, good_response])

        result = await run_breakdown(parsed, invoker, concurrency=1)

        assert len(invoker.prompts) == 2
        assert result.retried_chunks == [0]
        assert result.elements[0].pages == [4]


class TestCrossChunkMerge:
    async def test_same_character_different_pages_across_chunks_unions_pages(self):
        # 15 pages, chunk_size=12, overlap=2 → chunk 0 covers 1-12, chunk 1 covers 11-15.
        parsed = make_parsed(15)
        chunks = chunk_pages(parsed.pages, chunk_size=12, overlap=2)
        assert len(chunks) == 2

        response_0 = extraction_json(
            [element_dict(category="character_name", text="Dana", pages=[2])]
        )
        response_1 = extraction_json(
            [element_dict(category="character_name", text="Dana", pages=[13])]
        )
        invoker = QueuedInvoker([response_0, response_1])

        result = await run_breakdown(parsed, invoker, concurrency=1)

        assert result.chunk_count == 2
        assert result.retried_chunks == []
        assert len(result.elements) == 1
        assert result.elements[0].pages == [2, 13]
        assert len(invoker.prompts) == 2


class TestFenceStripping:
    async def test_fenced_json_response_parses_without_retry(self):
        parsed = make_parsed(7)
        raw_json = extraction_json(
            [element_dict(category="character_name", text="Eve", pages=[1])]
        )
        fenced_response = f"```json\n{raw_json}\n```"
        invoker = QueuedInvoker([fenced_response])

        result = await run_breakdown(parsed, invoker, concurrency=1)

        assert len(invoker.prompts) == 1  # no retry needed
        assert result.retried_chunks == []
        assert len(result.elements) == 1
        assert result.elements[0].text == "Eve"

    async def test_bare_fence_without_language_tag(self):
        parsed = make_parsed(7)
        raw_json = extraction_json(
            [element_dict(category="character_name", text="Frank", pages=[1])]
        )
        fenced_response = f"```\n{raw_json}\n```"
        invoker = QueuedInvoker([fenced_response])

        result = await run_breakdown(parsed, invoker, concurrency=1)

        assert len(invoker.prompts) == 1
        assert result.elements[0].text == "Frank"

    async def test_bare_json_passes_through_unchanged(self):
        chunks = chunk_pages(make_pages(7), chunk_size=12, overlap=2)
        chunk = chunks[0]
        raw_json = extraction_json(
            [element_dict(category="character_name", text="Grace", pages=[1])]
        )
        invoker = QueuedInvoker([raw_json])

        extraction = await extract_chunk(invoker, chunk)

        assert len(invoker.prompts) == 1
        assert extraction.elements[0].text == "Grace"
