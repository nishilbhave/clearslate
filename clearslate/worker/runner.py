"""RunWorker: executes the breakdown stage for a run and persists results.

Phase 1 passes the already-parsed script directly to `execute_breakdown`
rather than round-tripping it through the `RunStore` — the in-memory store
has no need to persist script sources, and the worker is invoked right after
parsing, in the same request flow that produced the `ParsedScript`. Phase 2's
`FirestoreRunStore` will persist uploaded sources to GCS; if a future phase
needs to resume/replay a breakdown from a stored source, that can be layered
on top of this same `execute_breakdown(run_id, parsed)` signature.
"""
from __future__ import annotations

from collections import Counter

from clearslate.agents.invoker import AgentInvoker
from clearslate.breakdown.stage import run_breakdown
from clearslate.costs import estimate_cost
from clearslate.errors import ClearSlateError
from clearslate.models import ParsedScript, RunState
from clearslate.store.base import RunStore


class RunWorker:
    """Runs the breakdown stage for a single run and writes results to `store`."""

    def __init__(self, store: RunStore, invoker: AgentInvoker) -> None:
        self.store = store
        self.invoker = invoker

    async def execute_breakdown(self, run_id: str, parsed: ParsedScript) -> None:
        """Run the breakdown pipeline for `run_id` against `parsed`.

        Never raises: any `ClearSlateError` (e.g. `BreakdownStageError`) or
        unexpected exception is caught and recorded on the run record as
        `state=FAILED` with an `error` string, so a background task failure
        always lands visibly on the run rather than dying silently.
        """
        try:
            await self.store.update_run(run_id, state=RunState.BREAKDOWN)

            result = await run_breakdown(parsed, self.invoker)
            await self.store.put_elements(run_id, result.elements)

            counts_by_category = Counter(element.category for element in result.elements)
            cost_estimate = estimate_cost(dict(counts_by_category), parsed.page_count)

            await self.store.update_run(
                run_id,
                element_count=len(result.elements),
                counts_by_category=dict(counts_by_category),
                cost_estimate=cost_estimate,
                state=RunState.AWAITING_START,
            )
        except ClearSlateError as e:
            await self.store.update_run(
                run_id, state=RunState.FAILED, error=f"{e.code}: {e.message}"
            )
        except Exception as e:  # noqa: BLE001 - background task must never die silently
            await self.store.update_run(
                run_id, state=RunState.FAILED, error=f"internal_error: {e}"
            )
