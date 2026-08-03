"""Offline extraction eval: replays recorded golden-script fixtures (Task 1.12).

Runs the real breakdown pipeline (chunk -> extract -> dedupe) against
`tests/fixtures/golden_breakdown/` via `FixtureInvoker` — no network/GCP calls, so
this runs in the default `uv run pytest` suite. The fixtures are recorded LIVE by
`scripts/record_golden_fixtures.py`; re-record and re-commit them after any
`INSTRUCTION` tuning in `clearslate/agents/breakdown/agent.py`.

Thresholds (never lower these — tune the extraction prompt instead):
    recall        >= 0.88   (matched plants / 25)
    page_hit_rate >= 0.85   (among matched plants)
    len(elements) <= 60     (precision guard: no hallucinated flood)
    categories    == all 9  ({e.category for e in elements} == set(ElementCategory))
"""
import json
from pathlib import Path

from clearslate.agents.invoker import FixtureInvoker
from clearslate.breakdown.golden_eval import compute_metrics
from clearslate.breakdown.stage import run_breakdown
from clearslate.models import ElementCategory
from clearslate.parsing.fountain import parse_fountain

GOLDEN_DIR = Path(__file__).parent.parent / "golden"
SCRIPT_PATH = GOLDEN_DIR / "the_comped_table.fountain"
MANIFEST_PATH = GOLDEN_DIR / "manifest.json"
FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "golden_breakdown"


async def test_golden_extraction_meets_thresholds():
    parsed = parse_fountain(SCRIPT_PATH.read_text())
    plants = json.loads(MANIFEST_PATH.read_text())["plants"]

    result = await run_breakdown(parsed, FixtureInvoker(FIXTURE_DIR))
    metrics = compute_metrics(plants, result.elements)

    assert metrics.recall >= 0.88, (
        f"recall {metrics.recall:.3f} < 0.88 "
        f"({len(metrics.matched)}/{len(plants)} plants matched); "
        f"missed plants: {metrics.missed_plant_ids}"
    )

    assert metrics.page_hit_rate >= 0.85, (
        f"page_hit_rate {metrics.page_hit_rate:.3f} < 0.85; "
        f"matched-but-page-missed plants: "
        f"{[m.plant_id for m in metrics.matched if not m.page_hit]}; "
        f"missed plants: {metrics.missed_plant_ids}"
    )

    assert len(result.elements) <= 60, (
        f"element count {len(result.elements)} > 60 "
        f"(precision guard tripped — possible hallucinated flood)"
    )

    categories_found = {e.category for e in result.elements}
    assert categories_found == set(ElementCategory), (
        f"missing categories: "
        f"{sorted(c.value for c in set(ElementCategory) - categories_found)}; "
        f"missed plants: {metrics.missed_plant_ids}"
    )
