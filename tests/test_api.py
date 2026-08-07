"""Tests for the FastAPI app: POST/GET runs and elements endpoints (Task 1.11)."""
from __future__ import annotations

import asyncio
import json

from httpx import ASGITransport, AsyncClient

from clearslate.agents.invoker import QueuedInvoker
from clearslate.api.app import create_app
from clearslate.config import settings
from clearslate.store.memory import InMemoryRunStore

FOUNTAIN_TEXT = """INT. KITCHENS - DAY

ALICE picks up the phone and calls Acme Corp.

EXT. PARKING LOT - DAY

BOB drives away in his car.
"""


def two_element_response() -> str:
    """A valid single-chunk `ChunkExtraction` JSON with 2 elements, pages in bounds."""
    return json.dumps(
        {
            "elements": [
                {
                    "category": "character_name",
                    "text": "Alice",
                    "pages": [1],
                    "scene": "INT. KITCHENS - DAY",
                    "context_snippet": "ALICE picks up the phone and calls Acme Corp.",
                },
                {
                    "category": "business_org",
                    "text": "Acme Corp",
                    "pages": [1],
                    "scene": "INT. KITCHENS - DAY",
                    "context_snippet": "ALICE picks up the phone and calls Acme Corp.",
                },
            ]
        }
    )


class _BlockingInvoker:
    """Test-only invoker whose `invoke()` blocks until `release()` is called.

    Used to deterministically observe a run mid-flight (before its background
    task completes). `QueuedInvoker`'s canned responses resolve without any
    real suspension, so a request/response round trip through the ASGI
    transport can give the background task enough event-loop turns to run to
    completion before the test ever checks state — a genuine invoker-level
    gate removes that race entirely.
    """

    def __init__(self) -> None:
        self._gate = asyncio.Event()

    def release(self) -> None:
        self._gate.set()

    async def invoke(self, prompt: str) -> str:
        await self._gate.wait()
        return json.dumps({"elements": []})


async def _drain(app) -> None:
    tasks = list(app.state.background_tasks)
    if tasks:
        await asyncio.gather(*tasks)


async def test_post_paste_then_drain_reaches_awaiting_start_with_two_elements():
    invoker = QueuedInvoker([two_element_response()])
    app = create_app(store=InMemoryRunStore(), invoker=invoker)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/runs", data={"text": FOUNTAIN_TEXT})
        assert resp.status_code == 202
        body = resp.json()
        assert body["run_id"].startswith("run_")
        assert body["state"] in ("PENDING", "BREAKDOWN")
        assert body["page_count"] == 1
        assert body["cost_estimate"]["basis"] == "pages"
        run_id = body["run_id"]

        await _drain(app)

        status_resp = await client.get(f"/api/runs/{run_id}")
        assert status_resp.status_code == 200
        status = status_resp.json()
        assert status["state"] == "AWAITING_START"
        assert status["element_count"] == 2
        assert sum(status["counts_by_category"].values()) == 2
        assert status["cost_estimate"]["basis"] == "elements"
        assert status["error"] is None

        elements_resp = await client.get(f"/api/runs/{run_id}/elements")
        assert elements_resp.status_code == 200
        elements_body = elements_resp.json()
        assert elements_body["run_id"] == run_id
        elements = elements_body["elements"]
        assert len(elements) == 2
        for element in elements:
            assert element["grade"] is None
            assert element["rule_citation"] is None
            assert element["alternatives"] == []
            assert element["pages"] == [1]


async def test_post_neither_file_nor_text_returns_422_empty_input():
    app = create_app(store=InMemoryRunStore(), invoker=QueuedInvoker([]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/runs", data={})

    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "empty_input"


async def test_post_over_page_limit_paste_returns_413():
    app = create_app(store=InMemoryRunStore(), invoker=QueuedInvoker([]))
    long_text = "line\n" * ((settings.max_pages + 1) * 55)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/runs", data={"text": long_text})

    assert resp.status_code == 413
    assert resp.json()["detail"]["code"] == "too_long"


async def test_get_unknown_run_returns_404():
    app = create_app(store=InMemoryRunStore(), invoker=QueuedInvoker([]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/runs/run_doesnotexist")

    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "not_found"


async def test_elements_before_completion_returns_409():
    invoker = _BlockingInvoker()
    app = create_app(store=InMemoryRunStore(), invoker=invoker)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/runs", data={"text": FOUNTAIN_TEXT})
        assert resp.status_code == 202
        run_id = resp.json()["run_id"]

        # The worker is blocked mid-breakdown (invoker gate not released yet):
        # elements are not ready.
        elements_resp = await client.get(f"/api/runs/{run_id}/elements")
        assert elements_resp.status_code == 409
        assert elements_resp.json()["detail"]["code"] == "not_ready"

        run_resp = await client.get(f"/api/runs/{run_id}")
        assert run_resp.json()["state"] in ("PENDING", "BREAKDOWN")

        invoker.release()
        await _drain(app)


async def test_get_elements_unknown_run_returns_404():
    app = create_app(store=InMemoryRunStore(), invoker=QueuedInvoker([]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/runs/run_doesnotexist/elements")

    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "not_found"


async def test_invalid_twice_invoker_fails_run():
    # NOTE: deviation from the task-1.11 brief. The brief's one-line summary says the
    # FAILED run's `error` should start with "invalid_llm_output" — but that is the
    # *chunk-level* `ExtractionValidationError` code raised inside
    # `clearslate/breakdown/stage.py::_extract_chunk_with_retry`. `run_breakdown`
    # catches that per-chunk, collects every failed chunk index, and re-raises a
    # single `BreakdownStageError(code="chunks_failed", ...)` (see
    # tests/test_stage.py::TestHardFail, Task 1.9's pinned interface). `RunWorker`
    # only ever sees that run-level `BreakdownStageError`, so the error recorded on
    # the run is "chunks_failed: ...", not "invalid_llm_output: ...". This test
    # asserts the real (run-level) code per the binding implementation decision.
    invoker = QueuedInvoker(["not json", "still not json"])
    app = create_app(store=InMemoryRunStore(), invoker=invoker)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/runs", data={"text": FOUNTAIN_TEXT})
        run_id = resp.json()["run_id"]

        await _drain(app)

        status_resp = await client.get(f"/api/runs/{run_id}")
        status = status_resp.json()
        assert status["state"] == "FAILED"
        assert status["error"].startswith("chunks_failed")

        elements_resp = await client.get(f"/api/runs/{run_id}/elements")
        assert elements_resp.status_code == 409
