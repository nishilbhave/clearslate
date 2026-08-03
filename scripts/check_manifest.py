"""Verify tests/golden/manifest.json plants against the_comped_table.fountain.

Deterministic, no LLM: parses the golden script with parse_fountain, then for
each manifest plant checks that at least one alias (case-insensitive substring)
appears on every page listed in expected_pages, and that aliases appear on at
most one page outside expected_pages.

Usage: uv run python scripts/check_manifest.py
"""
import json
import sys
from pathlib import Path

from clearslate.parsing.fountain import parse_fountain

GOLDEN_DIR = Path(__file__).parent.parent / "tests" / "golden"
SCRIPT_PATH = GOLDEN_DIR / "the_comped_table.fountain"
MANIFEST_PATH = GOLDEN_DIR / "manifest.json"


def page_has_alias(page_text: str, aliases: list[str]) -> bool:
    """True if any alias appears in page_text as a case-insensitive substring."""
    lowered = page_text.lower()
    return any(alias.lower() in lowered for alias in aliases)


def check_plant(plant: dict, pages: dict[int, str]) -> tuple[bool, str]:
    """Check one manifest plant. Returns (passed, reason-if-failed)."""
    aliases = plant["match_aliases"]
    expected_pages = set(plant["expected_pages"])

    missing = [p for p in sorted(expected_pages) if not page_has_alias(pages[p], aliases)]
    if missing:
        return False, f"missing on expected page(s) {missing}"

    outside_hits = [
        p for p in sorted(pages) if p not in expected_pages and page_has_alias(pages[p], aliases)
    ]
    if len(outside_hits) > 1:
        return False, f"found on {len(outside_hits)} unexpected page(s) {outside_hits} (max 1 allowed)"

    return True, ""


def main() -> int:
    script_text = SCRIPT_PATH.read_text()
    manifest = json.loads(MANIFEST_PATH.read_text())

    parsed = parse_fountain(script_text)
    pages = {p.page: p.text for p in parsed.pages}

    if parsed.page_count != manifest["pages"]:
        print(
            f"FATAL: parsed page_count={parsed.page_count} != manifest pages={manifest['pages']}"
        )
        return 1

    plants = manifest["plants"]
    passed_count = 0
    failed_ids: list[str] = []

    for plant in plants:
        ok, reason = check_plant(plant, pages)
        status = "PASS" if ok else "FAIL"
        line = f"{status}  {plant['plant_id']}  {plant['category']:<18}  {plant['surface_text']!r}"
        if not ok:
            line += f"  -- {reason}"
            failed_ids.append(plant["plant_id"])
        else:
            passed_count += 1
        print(line)

    print(f"\n{passed_count}/{len(plants)} plants verified")

    if failed_ids:
        print(f"FAILED: {', '.join(failed_ids)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
