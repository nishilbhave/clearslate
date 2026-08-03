"""RunStore protocol: persistence for run records and their extracted elements.

Shaped 1:1 to the spec's Firestore collections so a Phase 2 `FirestoreRunStore`
(storing run docs in Firestore and uploaded sources in GCS) is a drop-in swap
behind this same interface.
"""
from __future__ import annotations

from typing import Protocol

from clearslate.models import Element, RunRecord


class RunStore(Protocol):
    async def create_run(self, run: RunRecord) -> None: ...

    async def get_run(self, run_id: str) -> RunRecord | None: ...

    async def update_run(self, run_id: str, **fields: object) -> None:
        """Update fields on an existing run record.

        Raises:
            KeyError: if `run_id` is not known to the store.
        """
        ...

    async def put_elements(self, run_id: str, elements: list[Element]) -> None: ...

    async def get_elements(self, run_id: str) -> list[Element]: ...
