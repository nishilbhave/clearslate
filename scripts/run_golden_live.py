"""Re-baselining tool: run the golden-script breakdown LIVE and print eval metrics.

Same extraction as `record_golden_fixtures.py` but against a bare `LocalAdkInvoker`
(no `RecordingInvoker` — nothing is written to the fixture directory). Prints the
element table plus the Task 1.12 eval metrics (recall, page-hit rate, element count,
categories present) computed against `tests/golden/manifest.json`, so you can check
whether a prompt/instruction tweak would clear the bar *before* burning a recording
run and committing new fixtures.

Requires live GCP credentials:

    set -a; source .env; set +a
    uv run python scripts/run_golden_live.py
"""
from __future__ import annotations

import asyncio
import json
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from clearslate.agents.invoker import LocalAdkInvoker
from clearslate.breakdown.golden_eval import compute_metrics
from clearslate.breakdown.stage import run_breakdown
from clearslate.models import ElementCategory
from clearslate.parsing.fountain import parse_fountain

load_dotenv()

GOLDEN_DIR = Path(__file__).parent.parent / "tests" / "golden"
SCRIPT_PATH = GOLDEN_DIR / "the_comped_table.fountain"
MANIFEST_PATH = GOLDEN_DIR / "manifest.json"


async def main() -> None:
    parsed = parse_fountain(SCRIPT_PATH.read_text())
    plants = json.loads(MANIFEST_PATH.read_text())["plants"]

    result = await run_breakdown(parsed, LocalAdkInvoker())

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

    metrics = compute_metrics(plants, result.elements)
    all_categories = set(ElementCategory)
    missing_categories = all_categories - metrics.categories_present

    print("\n=== Eval metrics ===")
    print(f"recall            {metrics.recall:.3f}  (threshold >= 0.88)"
          f"  [{len(metrics.matched)}/{len(plants)} plants matched]")
    print(f"page_hit_rate     {metrics.page_hit_rate:.3f}  (threshold >= 0.85)"
          f"  [{sum(1 for m in metrics.matched if m.page_hit)}/{len(metrics.matched)} matched-hit]")
    print(f"element_count     {metrics.element_count}  (threshold <= 60)")
    print(f"categories        {len(metrics.categories_present)}/9 present"
          f"  (threshold: all 9)")
    if missing_categories:
        print(f"  missing: {sorted(c.value for c in missing_categories)}")
    if metrics.missed_plant_ids:
        print(f"missed plants:    {metrics.missed_plant_ids}")

    passed = (
        metrics.recall >= 0.88
        and metrics.page_hit_rate >= 0.85
        and metrics.element_count <= 60
        and not missing_categories
    )
    print(f"\n{'PASS' if passed else 'FAIL'} — thresholds "
          f"{'met' if passed else 'NOT met'}")


if __name__ == "__main__":
    asyncio.run(main())
