"""In-memory `RunStore` implementation for Phase 1.

Dict-backed, single-process, not durable across restarts. The worker
(`clearslate.worker.runner.RunWorker`) receives the already-parsed script
directly as an argument rather than round-tripping it through the store, so
this store does not need to persist `ParsedScript` sources. Phase 2's
`FirestoreRunStore` will persist run records to a Firestore collection and
uploaded script sources to GCS behind the same `RunStore` protocol.
"""
from __future__ import annotations

from clearslate.models import Element, RunRecord


class InMemoryRunStore:
    """Dict-backed `RunStore` for tests and local/single-process serving."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._elements: dict[str, list[Element]] = {}

    async def create_run(self, run: RunRecord) -> None:
        self._runs[run.run_id] = run

    async def get_run(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    async def update_run(self, run_id: str, **fields: object) -> None:
        if run_id not in self._runs:
            raise KeyError(run_id)
        self._runs[run_id] = self._runs[run_id].model_copy(update=fields)

    async def put_elements(self, run_id: str, elements: list[Element]) -> None:
        self._elements[run_id] = list(elements)

    async def get_elements(self, run_id: str) -> list[Element]:
        return list(self._elements.get(run_id, []))
