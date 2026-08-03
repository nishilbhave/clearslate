"""Live smoke test: `LocalAdkInvoker` actually calls Gemini via Vertex AI.

Gated behind the `live` marker (default `addopts = "-m 'not live'"` in
`pyproject.toml` excludes it from the normal offline suite), so this only runs when
explicitly requested with real GCP credentials:

    set -a; source .env; set +a
    uv run pytest -m live -o addopts='' -q
"""
import pytest

from clearslate.agents.invoker import LocalAdkInvoker
from clearslate.breakdown.stage import run_breakdown
from clearslate.parsing.fountain import parse_fountain

# Original 2-page mini-script: one obvious character (Wren Okafor-Delacroix) and one
# obvious brand (Red Bull), plus incidental business_org (Sysco) for headroom above
# the >=3 element floor.
MINI_SCRIPT = """Title: Loading Dock Blues
Author: ClearSlate Live Smoke
Draft date: August 3, 2026

INT. LOADING DOCK - NIGHT

Fluorescent light hums over stacked pallets. Forklifts idle in a row like sleeping animals.

WREN OKAFOR-DELACROIX, thirty, exhausted, clipboard in hand, checks a shipment against a manifest.

WREN
Eleven o'clock and Sysco still hasn't shown. Somebody call the depot.

A radio crackles somewhere behind the pallets. Rain starts against the corrugated roof.

WREN (CONT'D)
Third night this week. If dispatch loses this account we're all reading want ads by Friday.

She kicks a pallet in frustration, then immediately regrets it and checks her boot for damage.

WREN (CONT'D)
Great. Steel-toe, meet actual toe.

She limps to the vending machine bolted to the wall, cracks open a can of Red Bull, drinks half of it in one go.

WREN (CONT'D)
(to herself)
Okay. Diagnostics. Manifest says forty crates. I count thirty-one. Somebody's doing math with their feelings again.

Headlights sweep across the loading dock. A truck finally backs in, brakes hissing in the wet air.

WREN (CONT'D)
About time.

She sets down the can and grabs her handheld scanner, walking out toward the truck as the rain picks up.

The dock door rattles upward on its chain, flooding the bay with white headlight glare.

WREN (CONT'D)
(shouting over the engine)
Back it up two more feet, you're blocking the ramp!

INT. LOADING DOCK - CONTINUOUS

The truck driver climbs down, waving an apology. Wren waves back, already scanning boxes with the handheld reader.

WREN
Just get it inside before the rain finds the good stuff.

She scans another crate. The reader beeps green and she nods to herself.

WREN (CONT'D)
There we go. One thirty-one down, nine to go.

The driver hands her a clipboard to sign. She scrawls her initials without looking up from the scanner.

WREN (CONT'D)
Tell dispatch Sysco owes us an apology and a discount.

DRIVER
I just drive the truck.

WREN
Lucky you.

She waves the last pallet through, the dock door rattling back down behind it, and finally lets herself breathe.
"""


@pytest.mark.live
async def test_live_breakdown_extracts_character_and_elements():
    parsed = parse_fountain(MINI_SCRIPT)
    assert parsed.page_count == 2  # sanity: really is the intended 2-page script

    result = await run_breakdown(parsed, LocalAdkInvoker())

    assert len(result.elements) >= 3, f"expected >=3 elements, got {result.elements}"

    normalized_texts = {e.normalized_text for e in result.elements}
    assert any("wren" in text for text in normalized_texts), (
        f"expected Wren Okafor-Delacroix among extracted elements: {normalized_texts}"
    )
