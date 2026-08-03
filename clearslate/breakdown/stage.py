"""
Breakdown stage: schema validation, one feedback retry, hard-fail, fan-out, dedup assembly.

Pipeline: chunk_pages → per-chunk extract_chunk (validate → on failure, one retry with the
prior errors folded into the prompt → on second failure, raise) → fan out with bounded
concurrency → merge into deduped Element records.
"""
from __future__ import annotations

import asyncio
import json

from pydantic import BaseModel, ValidationError

from clearslate.agents.breakdown.schema import ChunkExtraction
from clearslate.agents.invoker import AgentInvoker
from clearslate.breakdown.chunker import Chunk, build_chunk_prompt, chunk_pages
from clearslate.breakdown.dedupe import RawExtractedElement, dedupe_elements
from clearslate.config import settings
from clearslate.errors import BreakdownStageError, ExtractionValidationError
from clearslate.models import Element, ElementCategory, ParsedScript


class BreakdownResult(BaseModel):
    """Assembled output of the breakdown stage."""

    elements: list[Element]
    chunk_count: int
    retried_chunks: list[int]  # visible, never silent


class _ValidationFailure(Exception):
    """Internal signal: a single extraction attempt failed schema/page-bounds validation.

    Never escapes this module — `extract_chunk`/`run_breakdown` callers only ever see
    `ExtractionValidationError` (after both attempts are exhausted) or a valid result.
    """


def _strip_code_fence(text: str) -> str:
    """Strip a leading/trailing ```-fence line pair if present; bare JSON passes through as-is."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return text
    lines = stripped.splitlines()
    if not lines:
        return text
    if len(lines) > 1 and lines[-1].strip() == "```":
        body = lines[1:-1]
    else:
        body = lines[1:]
    return "\n".join(body)


def _check_page_bounds(extraction: ChunkExtraction, chunk: Chunk) -> None:
    """Raise `_ValidationFailure` if any element cites empty or out-of-range pages."""
    offending: list[tuple[str, list[int]]] = []
    for element in extraction.elements:
        if not element.pages:
            offending.append((element.text, element.pages))
            continue
        if any(page < chunk.start_page or page > chunk.end_page for page in element.pages):
            offending.append((element.text, element.pages))
    if offending:
        raise _ValidationFailure(
            f"elements cite pages outside chunk bounds [{chunk.start_page}, {chunk.end_page}] "
            f"(or empty pages): {offending}"
        )


def _parse_and_validate(response: str, chunk: Chunk) -> ChunkExtraction:
    """json.loads (after fence-stripping) → ChunkExtraction.model_validate → page-bounds check.

    Raises `_ValidationFailure` with a concise description on any failure.
    """
    cleaned = _strip_code_fence(response)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise _ValidationFailure(f"invalid JSON: {exc}") from exc

    try:
        extraction = ChunkExtraction.model_validate(data)
    except ValidationError as exc:
        raise _ValidationFailure(f"schema validation failed: {exc}") from exc

    _check_page_bounds(extraction, chunk)
    return extraction


async def _extract_chunk_with_retry(
    invoker: AgentInvoker, chunk: Chunk
) -> tuple[ChunkExtraction, bool]:
    """Core validate → one retry → hard-fail logic. Returns (extraction, did_retry)."""
    prompt = build_chunk_prompt(chunk)
    response = await invoker.invoke(prompt)
    try:
        return _parse_and_validate(response, chunk), False
    except _ValidationFailure as first_error:
        retry_prompt = (
            f"{prompt}\nYour previous output failed validation:\n{first_error}\n"
            "Return corrected JSON only."
        )
        retry_response = await invoker.invoke(retry_prompt)
        try:
            return _parse_and_validate(retry_response, chunk), True
        except _ValidationFailure as second_error:
            raise ExtractionValidationError(
                "invalid_llm_output",
                f"chunk {chunk.index} (pages {chunk.start_page}-{chunk.end_page}) failed "
                f"validation after retry: {second_error}",
            ) from second_error


async def extract_chunk(invoker: AgentInvoker, chunk: Chunk) -> ChunkExtraction:
    """Extract elements from one chunk: validate → one retry with feedback → hard-fail.

    Raises `ExtractionValidationError` if both attempts fail validation.
    """
    extraction, _retried = await _extract_chunk_with_retry(invoker, chunk)
    return extraction


async def run_breakdown(
    parsed: ParsedScript, invoker: AgentInvoker, *, concurrency: int = 4
) -> BreakdownResult:
    """Fan out extraction across chunks and assemble a deduped `BreakdownResult`.

    Any `ExtractionValidationError` from a chunk is collected and re-raised as a single
    `BreakdownStageError` naming every failed chunk. Any other exception type propagates
    unchanged (a bug should never be silently repackaged as a stage error).
    """
    chunks = chunk_pages(parsed.pages, chunk_size=settings.chunk_pages, overlap=settings.chunk_overlap)
    semaphore = asyncio.Semaphore(concurrency)

    async def _run(chunk: Chunk) -> tuple[ChunkExtraction, bool]:
        async with semaphore:
            return await _extract_chunk_with_retry(invoker, chunk)

    results = await asyncio.gather(*(_run(chunk) for chunk in chunks), return_exceptions=True)

    failed_indices: list[int] = []
    retried_chunks: list[int] = []
    raw_elements: list[RawExtractedElement] = []

    for chunk, result in zip(chunks, results, strict=True):
        if isinstance(result, ExtractionValidationError):
            failed_indices.append(chunk.index)
            continue
        if isinstance(result, BaseException):
            raise result

        extraction, retried = result
        if retried:
            retried_chunks.append(chunk.index)
        for element in extraction.elements:
            raw_elements.append(
                RawExtractedElement(
                    category=ElementCategory(element.category),
                    text=element.text,
                    pages=element.pages,
                    scene=element.scene,
                    context_snippet=element.context_snippet,
                    chunk_index=chunk.index,
                )
            )

    if failed_indices:
        raise BreakdownStageError(
            "chunks_failed",
            f"chunks {sorted(failed_indices)} failed validation after retry",
        )

    elements = dedupe_elements(raw_elements)
    return BreakdownResult(
        elements=elements,
        chunk_count=len(chunks),
        retried_chunks=sorted(retried_chunks),
    )
