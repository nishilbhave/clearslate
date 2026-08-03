#!/usr/bin/env python3
"""Generate fixture PDF for tests."""
from pathlib import Path

from fpdf import FPDF


def make_fixture_pdf() -> None:
    """Generate a two-page PDF with page markers for testing."""
    pdf = FPDF()

    # Page 1
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "PAGE-ONE-MARKER", ln=True)
    pdf.cell(0, 10, "INT. DINER - DAY", ln=True)
    for i in range(5):
        pdf.cell(0, 10, "Filler line for extraction.", ln=True)

    # Page 2
    pdf.add_page()
    pdf.cell(0, 10, "PAGE-TWO-MARKER", ln=True)
    for i in range(5):
        pdf.cell(0, 10, "Filler line for extraction.", ln=True)

    # Write to fixtures directory
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    output_path = fixtures_dir / "two_page.pdf"

    pdf.output(str(output_path))
    print(f"Created {output_path}")


if __name__ == "__main__":
    make_fixture_pdf()
