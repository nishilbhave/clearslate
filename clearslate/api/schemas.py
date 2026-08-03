"""Wire schemas for the ClearSlate HTTP API."""
from __future__ import annotations

from pydantic import BaseModel

from clearslate.models import CostEstimate, Element, ElementCategory, RunState


class RunCreated(BaseModel):
    """Response body for `POST /api/runs`."""

    run_id: str
    state: RunState
    page_count: int
    element_estimate: int
    cost_estimate: CostEstimate  # basis="pages"


class RunStatus(BaseModel):
    """Response body for `GET /api/runs/{run_id}`; mirrors `RunRecord`."""

    run_id: str
    state: RunState
    page_count: int
    element_count: int | None = None
    counts_by_category: dict[ElementCategory, int] | None = None
    cost_estimate: CostEstimate | None = None
    error: str | None = None


class ElementList(BaseModel):
    """Response body for `GET /api/runs/{run_id}/elements`."""

    run_id: str
    elements: list[Element]
