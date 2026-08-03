"""FastAPI app: POST/GET runs and elements endpoints (Phase 1).

Phase 2 adds `POST .../start`, `GET .../events` (SSE), `/report`, `/report.pdf`.
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

from clearslate.agents.invoker import AgentEngineInvoker, AgentInvoker, LocalAdkInvoker
from clearslate.api.schemas import ElementList, RunCreated, RunStatus
from clearslate.config import settings
from clearslate.costs import ELEMENTS_PER_PAGE, estimate_from_pages
from clearslate.errors import ParserError
from clearslate.models import RunRecord, RunState
from clearslate.parsing.router import parse_upload
from clearslate.store.base import RunStore
from clearslate.store.memory import InMemoryRunStore
from clearslate.worker.runner import RunWorker

# States for which no elements have been stored yet (or ever will be, on failure).
_ELEMENTS_NOT_READY_STATES = {RunState.PENDING, RunState.BREAKDOWN, RunState.FAILED}


def _default_invoker() -> AgentInvoker:
    if settings.agent_runtime == "engine":
        return AgentEngineInvoker(settings.breakdown_engine_id, settings.project, settings.location)
    return LocalAdkInvoker()


def create_app(store: RunStore | None = None, invoker: AgentInvoker | None = None) -> FastAPI:
    app = FastAPI(title="ClearSlate")

    app.state.store = store if store is not None else InMemoryRunStore()
    # Resolved lazily on first run creation (not here) so importing/constructing the
    # app never triggers ADK/model init unless a run is actually created and no
    # invoker was injected.
    app.state.invoker = invoker
    app.state.background_tasks: set[asyncio.Task] = set()

    def _get_invoker() -> AgentInvoker:
        if app.state.invoker is None:
            app.state.invoker = _default_invoker()
        return app.state.invoker

    @app.post("/api/runs", status_code=202, response_model=RunCreated)
    async def create_run(
        file: UploadFile | None = File(default=None),
        text: str | None = Form(default=None),
    ) -> RunCreated:
        content = await file.read() if file is not None else None
        try:
            parsed = parse_upload(
                filename=file.filename if file is not None else None,
                content=content,
                pasted_text=text,
            )
        except ParserError as e:
            status_code = 413 if e.code == "too_long" else 422
            raise HTTPException(
                status_code=status_code, detail={"code": e.code, "message": e.message}
            ) from e

        run_id = f"run_{uuid4().hex[:12]}"
        run = RunRecord(
            run_id=run_id,
            state=RunState.PENDING,
            created_at=datetime.now(UTC),
            source_format=parsed.source_format,
            page_count=parsed.page_count,
        )
        await app.state.store.create_run(run)

        worker = RunWorker(app.state.store, _get_invoker())
        task = asyncio.create_task(worker.execute_breakdown(run_id, parsed))
        app.state.background_tasks.add(task)
        task.add_done_callback(app.state.background_tasks.discard)

        return RunCreated(
            run_id=run_id,
            state=run.state,
            page_count=parsed.page_count,
            element_estimate=int(parsed.page_count * ELEMENTS_PER_PAGE),
            cost_estimate=estimate_from_pages(parsed.page_count),
        )

    @app.get("/api/runs/{run_id}", response_model=RunStatus)
    async def get_run(run_id: str) -> RunStatus:
        run = await app.state.store.get_run(run_id)
        if run is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "not_found", "message": f"No run {run_id!r}."},
            )
        return RunStatus(
            run_id=run.run_id,
            state=run.state,
            page_count=run.page_count,
            element_count=run.element_count,
            counts_by_category=run.counts_by_category,
            cost_estimate=run.cost_estimate,
            error=run.error,
        )

    @app.get("/api/runs/{run_id}/elements", response_model=ElementList)
    async def get_elements(run_id: str) -> ElementList:
        run = await app.state.store.get_run(run_id)
        if run is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "not_found", "message": f"No run {run_id!r}."},
            )
        if run.state in _ELEMENTS_NOT_READY_STATES:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "not_ready",
                    "message": f"Run {run_id} has no elements yet (state={run.state.value}).",
                },
            )
        elements = await app.state.store.get_elements(run_id)
        return ElementList(run_id=run_id, elements=elements)

    # Static mount LAST: SPA fallback for the built frontend, if present.
    frontend_dist = Path("frontend/dist")
    if frontend_dist.exists():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True))

    return app


app = create_app()
