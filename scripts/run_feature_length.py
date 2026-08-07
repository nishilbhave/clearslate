"""Feature-length scale test: run a real screenplay through breakdown and report systems behavior.

The golden eval (`scripts/run_golden_live.py`) measures *extraction quality* on a 7-page
script that produces exactly one chunk. This script measures *systems behavior* at real
feature length -- multi-chunk fan-out, live dedupe across the 2-page chunk overlap,
all-or-nothing chunk failure, and how far the cost estimator's page heuristics drift from
observed token volume.

Two modes, same output shape, so local and deployed results diff directly:

    # 1. local baseline -- same code path Cloud Run runs (CLEARSLATE_AGENT_RUNTIME=local)
    set -a; source .env; set +a
    uv run python scripts/run_feature_length.py --local ~/path/to/screenplay.pdf

    # 2. deployed -- any divergence from the baseline is infrastructure, not the model
    uv run python scripts/run_feature_length.py \
        --remote https://your-cloud-run-service-url \
        ~/path/to/screenplay.pdf

Local mode wraps the real invoker in `RecordingInvoker`, so every raw model response is
written to disk as it arrives. A run that dies on one bad chunk still leaves every other
chunk's response available for offline analysis -- the paid work is never lost.

Reports are written to `--out` (default `.scale-test/`), which is gitignored.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from clearslate.agents.invoker import AgentInvoker, LocalAdkInvoker, RecordingInvoker
from clearslate.breakdown.stage import run_breakdown
from clearslate.config import settings
from clearslate.costs import TOKENS_PER_PAGE, estimate_cost, estimate_from_pages
from clearslate.errors import BreakdownStageError, ClearSlateError, ParserError
from clearslate.models import ElementCategory, RunState
from clearslate.parsing.router import parse_upload

load_dotenv()

# Rough chars-per-token for Gemini on English prose. Only used to compare observed volume
# against the estimator's TOKENS_PER_PAGE assumption -- not for billing.
CHARS_PER_TOKEN = 4.0

# `RunState` is a StrEnum whose values are upper-case ("AWAITING_START"), which is what the
# API serializes. Compared upper-cased so a lower-case literal can never silently poll forever.
TERMINAL_STATES = {RunState.AWAITING_START.value, RunState.FAILED.value}


@dataclass
class InvokerTally:
    """Counts prompts/responses flowing through the invoker, for token calibration."""

    calls: int = 0
    prompt_chars: int = 0
    response_chars: int = 0
    per_call_seconds: list[float] = field(default_factory=list)


class TallyingInvoker:
    """Wraps an `AgentInvoker`, recording call count, payload sizes, and per-call latency."""

    def __init__(self, inner: AgentInvoker, tally: InvokerTally) -> None:
        self._inner = inner
        self._tally = tally

    async def invoke(self, prompt: str) -> str:
        started = time.monotonic()
        response = await self._inner.invoke(prompt)
        self._tally.per_call_seconds.append(time.monotonic() - started)
        self._tally.calls += 1
        self._tally.prompt_chars += len(prompt)
        self._tally.response_chars += len(response)
        return response


def _parse(path: Path):
    """Parse the file through the real router, surfacing ParserError as a clean exit."""
    content = path.read_bytes()
    try:
        return parse_upload(filename=path.name, content=content, pasted_text=None)
    except ParserError as e:
        print(f"FAIL parse: {e.code}: {e.message}", file=sys.stderr)
        if e.code == "too_long":
            print(
                f"  (settings.max_pages is {settings.max_pages}; raise it or trim the file)",
                file=sys.stderr,
            )
        raise SystemExit(2) from e


def _print_category_table(counts: Counter[ElementCategory]) -> None:
    print("\nElements by category:")
    for category in ElementCategory:
        count = counts.get(category, 0)
        marker = "  " if count else "  << MISSING"
        print(f"  {category.value:<20} {count:>4}{marker}")


def _print_token_calibration(tally: InvokerTally, page_count: int) -> None:
    """Compare observed prompt volume against the estimator's TOKENS_PER_PAGE assumption."""
    if not tally.calls:
        return
    est_prompt_tokens = tally.prompt_chars / CHARS_PER_TOKEN
    est_response_tokens = tally.response_chars / CHARS_PER_TOKEN
    # Chunks overlap by `chunk_overlap` pages, so prompt volume exceeds a clean page count.
    observed_per_page = est_prompt_tokens / page_count if page_count else 0.0

    print("\nToken calibration (approx, chars/4):")
    print(f"  model calls            {tally.calls}")
    print(f"  prompt tokens  ~{est_prompt_tokens:>10,.0f}")
    print(f"  output tokens  ~{est_response_tokens:>10,.0f}")
    print(f"  observed prompt tokens/page  ~{observed_per_page:,.0f}")
    print(f"  estimator assumes            {TOKENS_PER_PAGE:,} (costs.py TOKENS_PER_PAGE)")
    drift = observed_per_page - TOKENS_PER_PAGE
    verdict = "over-estimates" if drift < 0 else "under-estimates"
    print(f"  -> estimator {verdict} prompt volume by ~{abs(drift):,.0f} tokens/page")

    if tally.per_call_seconds:
        ordered = sorted(tally.per_call_seconds)
        print(
            f"  per-call latency  min {ordered[0]:.1f}s  "
            f"median {ordered[len(ordered) // 2]:.1f}s  max {ordered[-1]:.1f}s"
        )


async def run_local(path: Path, out_dir: Path) -> dict:
    """Run breakdown in-process via the same code path the deployed service uses."""
    parsed = _parse(path)
    print(f"Parsed {path.name}: {parsed.page_count} pages, format={parsed.source_format}, "
          f"{len(parsed.scene_headings)} scene headings")

    prediction = estimate_from_pages(parsed.page_count)
    print(f"Pre-run estimate: {prediction.element_count} elements, "
          f"gemini ${prediction.gemini_usd} (parallel ${prediction.parallel_usd} is Phase 2, "
          f"not spent today)")

    responses_dir = out_dir / "responses"
    tally = InvokerTally()
    invoker = TallyingInvoker(RecordingInvoker(LocalAdkInvoker(), responses_dir), tally)

    print(f"\nRunning breakdown... (raw responses -> {responses_dir})")
    started = time.monotonic()
    failure: str | None = None
    result = None
    try:
        result = await run_breakdown(parsed, invoker)
    except BreakdownStageError as e:
        failure = f"{e.code}: {e.message}"
    except ClearSlateError as e:
        failure = f"{e.code}: {e.message}"
    elapsed = time.monotonic() - started

    print(f"Wall time: {elapsed:.1f}s")

    if failure is not None:
        print(f"\nFAIL breakdown: {failure}")
        print(
            f"  All completed chunks were discarded by stage.py's all-or-nothing raise.\n"
            f"  {tally.calls} model responses are preserved in {responses_dir} for offline\n"
            f"  analysis -- inspect them rather than paying for a second run."
        )
        _print_token_calibration(tally, parsed.page_count)
        return {
            "mode": "local",
            "source": str(path),
            "page_count": parsed.page_count,
            "failed": True,
            "error": failure,
            "elapsed_seconds": round(elapsed, 1),
            "model_calls": tally.calls,
        }

    assert result is not None
    counts = Counter(element.category for element in result.elements)
    actual = estimate_cost(dict(counts), parsed.page_count)

    print(f"\nChunks: {result.chunk_count}   retried: {result.retried_chunks or 'none'}")
    print(f"Elements after dedupe: {len(result.elements)}")
    _print_category_table(counts)

    print("\nEstimator accuracy:")
    print(f"  predicted from pages    {prediction.element_count} elements")
    print(f"  actually extracted      {len(result.elements)} elements")
    if prediction.element_count:
        ratio = len(result.elements) / prediction.element_count
        print(f"  ratio                   {ratio:.2f}x  "
              f"(ELEMENTS_PER_PAGE currently {actual.element_count / parsed.page_count:.2f}"
              f" observed)")
    _print_token_calibration(tally, parsed.page_count)

    payload = {
        "mode": "local",
        "source": str(path),
        "page_count": parsed.page_count,
        "failed": False,
        "elapsed_seconds": round(elapsed, 1),
        "chunk_count": result.chunk_count,
        "retried_chunks": result.retried_chunks,
        "element_count": len(result.elements),
        "counts_by_category": {
            category.value: n
            for category, n in sorted(counts.items(), key=lambda kv: kv[0].value)
        },
        "model_calls": tally.calls,
        "prompt_chars": tally.prompt_chars,
        "response_chars": tally.response_chars,
        "elements": [
            {"category": e.category.value, "text": e.text, "pages": e.pages}
            for e in result.elements
        ],
    }
    return payload


async def run_remote(path: Path, base_url: str, out_dir: Path) -> dict:
    """Upload to a deployed service and poll to a terminal state, recording infra faults."""
    import httpx

    base_url = base_url.rstrip("/")
    content = path.read_bytes()
    size_mb = len(content) / (1024 * 1024)
    print(f"Uploading {path.name} ({size_mb:.1f} MB) to {base_url}")

    poll_faults: list[dict] = []
    started = time.monotonic()

    async with httpx.AsyncClient(timeout=120.0) as client:
        upload_started = time.monotonic()
        response = await client.post(
            f"{base_url}/api/runs",
            files={"file": (path.name, content, "application/pdf")},
        )
        upload_seconds = time.monotonic() - upload_started

        if response.status_code != 202:
            print(f"FAIL upload: HTTP {response.status_code} {response.text[:400]}")
            return {
                "mode": "remote",
                "source": str(path),
                "failed": True,
                "error": f"upload_http_{response.status_code}",
                "body": response.text[:1000],
            }

        created = response.json()
        run_id = created["run_id"]
        print(f"  202 in {upload_seconds:.1f}s -> run_id={run_id}, "
              f"page_count={created['page_count']}, "
              f"estimate={created['cost_estimate']['total_usd']}")

        state = created["state"]
        status: dict = created
        while state not in TERMINAL_STATES:
            await asyncio.sleep(5)
            poll = await client.get(f"{base_url}/api/runs/{run_id}")
            if poll.status_code != 200:
                # A 404 here means the poll hit an instance that never saw this run --
                # the in-memory store is per-instance and maxScale is 2.
                fault = {
                    "at_seconds": round(time.monotonic() - started, 1),
                    "status_code": poll.status_code,
                    "body": poll.text[:300],
                }
                poll_faults.append(fault)
                print(f"  !! poll fault at {fault['at_seconds']}s: HTTP {poll.status_code} "
                      f"{poll.text[:160]}")
                continue
            status = poll.json()
            if status["state"] != state:
                state = status["state"]
                print(f"  [{time.monotonic() - started:6.1f}s] state -> {state}")

    elapsed = time.monotonic() - started
    print(f"\nTerminal state: {state} after {elapsed:.1f}s")
    if poll_faults:
        print(f"  {len(poll_faults)} poll fault(s) observed -- see report for details")

    elements: list[dict] = []
    if state == RunState.AWAITING_START.value:
        async with httpx.AsyncClient(timeout=120.0) as client:
            el_response = await client.get(f"{base_url}/api/runs/{run_id}/elements")
        if el_response.status_code == 200:
            elements = el_response.json()["elements"]
            print(f"Elements retrieved: {len(elements)}")
        else:
            print(f"FAIL elements: HTTP {el_response.status_code} {el_response.text[:300]}")
    else:
        print(f"Run error: {status.get('error')}")

    counts = Counter(e["category"] for e in elements)
    if counts:
        print("\nElements by category:")
        for category in ElementCategory:
            print(f"  {category.value:<20} {counts.get(category.value, 0):>4}")

    return {
        "mode": "remote",
        "source": str(path),
        "base_url": base_url,
        "run_id": run_id,
        "failed": state != RunState.AWAITING_START.value,
        "final_state": state,
        "error": status.get("error"),
        "upload_seconds": round(upload_seconds, 1),
        "elapsed_seconds": round(elapsed, 1),
        "upload_mb": round(size_mb, 2),
        "poll_faults": poll_faults,
        "element_count": len(elements),
        "counts_by_category": dict(counts),
        "elements": [
            {"category": e["category"], "text": e["text"], "pages": e["pages"]} for e in elements
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path, help="path to a screenplay PDF/fountain/txt")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--local", action="store_true", help="run breakdown in-process")
    mode.add_argument("--remote", metavar="BASE_URL", help="upload to a deployed service")
    parser.add_argument(
        "--out", type=Path, default=Path(".scale-test"), help="report directory"
    )
    args = parser.parse_args()

    if not args.script.exists():
        print(f"No such file: {args.script}", file=sys.stderr)
        raise SystemExit(2)

    args.out.mkdir(parents=True, exist_ok=True)

    if args.local:
        payload = asyncio.run(run_local(args.script, args.out))
        report_path = args.out / "local.json"
    else:
        payload = asyncio.run(run_remote(args.script, args.remote, args.out))
        report_path = args.out / "remote.json"

    report_path.write_text(json.dumps(payload, indent=2))
    print(f"\nReport written to {report_path}")


if __name__ == "__main__":
    main()
