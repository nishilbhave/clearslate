"""Record LIVE Gemini fixtures for the golden-script breakdown (Task 1.12).

Parses `tests/golden/the_comped_table.fountain` (7 pages -> one chunk, so one live
request) and runs the breakdown stage through a real `LocalAdkInvoker` wrapped in
`RecordingInvoker`, which writes prompt-keyed fixture JSON to
`tests/fixtures/golden_breakdown/` for later offline replay via `FixtureInvoker`
(see `tests/eval/test_golden_extraction.py`).

Requires live GCP credentials:

    set -a; source .env; set +a
    uv run python scripts/record_golden_fixtures.py

Re-run after tuning `INSTRUCTION` in `clearslate/agents/breakdown/agent.py` — delete
the old fixture file(s) first so the new prompt/response pair is written fresh.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from clearslate.agents.invoker import LocalAdkInvoker, RecordingInvoker
from clearslate.breakdown.stage import run_breakdown
from clearslate.parsing.fountain import parse_fountain

load_dotenv()

GOLDEN_DIR = Path(__file__).parent.parent / "tests" / "golden"
SCRIPT_PATH = GOLDEN_DIR / "the_comped_table.fountain"
FIXTURE_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "golden_breakdown"


async def main() -> None:
    parsed = parse_fountain(SCRIPT_PATH.read_text())
    invoker = RecordingInvoker(LocalAdkInvoker(), FIXTURE_DIR)

    result = await run_breakdown(parsed, invoker)

    print(f"{'page(s)':<12} {'category':<18} text")
    print("-" * 72)
    for element in result.elements:
        pages_str = ",".join(str(p) for p in element.pages)
        print(f"{pages_str:<12} {element.category.value:<18} {element.text}")

    counts = Counter(e.category.value for e in result.elements)
    print("\nCounts by category:")
    for category, count in sorted(counts.items()):
        print(f"  {category:<18} {count}")

    print(f"\nTotal elements: {len(result.elements)}")
    print(f"Chunk count:    {result.chunk_count}")
    print(f"Retried chunks: {result.retried_chunks}")
    print(f"\nFixtures written to {FIXTURE_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
