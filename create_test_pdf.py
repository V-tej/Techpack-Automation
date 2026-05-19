"""Generate a sample techpack PDF for testing the automation system.
Uses fpdf2 (pure Python, no DLL issues).
"""

from fpdf import FPDF
from pathlib import Path


def create_test_techpack():
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    def add_page(title, content_lines):
        pdf.add_page()
        pdf.set_font("Helvetica", style="B", size=20)
        pdf.set_fill_color(30, 30, 30)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.ln(6)
        pdf.set_text_color(0, 0, 0)
        for line in content_lines:
            if line.startswith("##"):
                pdf.set_font("Helvetica", style="B", size=13)
                pdf.cell(0, 8, line[2:].strip(), new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("Helvetica", size=11)
            elif line.startswith("--"):
                pdf.set_draw_color(200, 200, 200)
                pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 170, pdf.get_y())
                pdf.ln(4)
            elif line == "":
                pdf.ln(4)
            else:
                pdf.set_font("Helvetica", size=11)
                pdf.multi_cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")

    # ── Page 1: Cover ──
    pdf.add_page()
    pdf.set_font("Helvetica", style="B", size=36)
    pdf.set_text_color(30, 30, 30)
    pdf.ln(30)
    pdf.cell(0, 20, "TECHPACK", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=16)
    pdf.ln(10)
    pdf.cell(0, 10, "Brand: TestBrand", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "Style: SS25-001", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "Season: Spring / Summer 2025", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", style="I", size=13)
    pdf.ln(6)
    pdf.cell(0, 8, "Polo Shirt - Classic Fit", align="C", new_x="LMARGIN", new_y="NEXT")

    # ── Page 2: Front Chest Print ──
    add_page("ARTWORK: FRONT CHEST PRINT", [
        "## Artwork Type",
        "Technique: Screen Print",
        "Process: DTF (Direct to Film)",
        "--",
        "## Placement & Dimensions",
        "Placement: Left Chest",
        "Dimensions: 8cm x 6cm",
        "--",
        "## Color Specifications",
        "Colors: Pantone 185C (Red), White",
        "Number of Colors: 2",
        "Ink Type: Plastisol / Water-based print",
        "--",
        "## Notes",
        "Puff print effect on main logo text.",
        "Foil print on star detail.",
    ])

    # ── Page 3: Back Print ──
    add_page("ARTWORK: BACK PRINT", [
        "## Artwork Type",
        "Technique: Sublimation Print",
        "Process: Digital Print - Full Color Process",
        "--",
        "## Placement & Dimensions",
        "Placement: Center Back",
        "Dimensions: 25cm x 30cm",
        "--",
        "## Color Specifications",
        "Colors: Pantone 2728C (Blue), Pantone 109C (Yellow)",
        "Full color sublimation - no color restrictions",
        "--",
        "## Notes",
        "Discharge print base required before sublimation.",
    ])

    # ── Page 4: Embroidery ──
    add_page("ARTWORK: SLEEVE EMBROIDERY", [
        "## Artwork Type",
        "Technique: Flat Embroidery",
        "Process: Satin Stitch + 3D Puff Embroidery",
        "--",
        "## Placement & Dimensions",
        "Placement: Right Sleeve",
        "Dimensions: 5cm x 3cm",
        "--",
        "## Thread Specifications",
        "Thread: Madeira 1147 (Navy), Madeira 1001 (White)",
        "Stitch Count: approx 8,500 stitches",
        "Backing: Cut-away backing required",
        "--",
        "## Notes",
        "3D puff on lettering only. Flat embroidery on icon.",
        "Embroidered patch sewn onto garment after production.",
    ])

    # ── Page 5: Woven Labels ──
    add_page("WOVEN LABEL SPECIFICATIONS", [
        "## Main Label",
        "Type: Damask Woven Label",
        "Size: 4cm x 2cm",
        "Placement: Neck Label - Center Back",
        "Colors: Navy + White thread",
        "--",
        "## Size Label",
        "Type: Satin Label",
        "Size: 2cm x 1.5cm",
        "Placement: Left Side Seam",
        "--",
        "## Care Label",
        "Type: Printed Taffeta Label",
        "Content: Standard wash care symbols + fiber content",
        "Placement: Right Side Seam, below size label",
        "--",
        "## Brand Label",
        "Woven tag attached to hangtag with brand logo",
    ])

    # ── Page 6: Patches & Badges ──
    add_page("PATCH & BADGE DETAILS", [
        "## Item 1: Rubber Patch",
        "Material: Silicone Badge - 3D molded rubber",
        "Placement: Left Sleeve",
        "Dimensions: 4cm x 4cm",
        "Colors: Navy + White",
        "--",
        "## Item 2: Leather Patch",
        "Material: PU Leather with deboss logo",
        "Placement: Hem - Right Side",
        "Dimensions: 6cm x 3cm",
        "Attachment: TPU patch backing, heat seal",
        "--",
        "## Item 3: Woven Patch",
        "Chenille patch on left chest (alternate colorway)",
        "PVC badge option available on request",
    ])

    # ── Page 7: Packaging ──
    add_page("PACKAGING ARTWORK", [
        "## Hangtag",
        "Size: 8cm x 5cm",
        "Material: 350gsm card stock",
        "Print: CMYK + Spot UV coating on logo",
        "String: White cotton string, 20cm",
        "--",
        "## Polybag",
        "Size: 30cm x 40cm, clear poly",
        "Sticker: Barcode + style info label",
        "Fold: Standard retail fold",
        "--",
        "## Price Tag",
        "Attached to hangtag with clear elastic loop",
        "--",
        "## Tissue Paper",
        "Branded tissue, single color print",
        "Packaging artwork must include recycling symbol",
    ])

    # ── Page 8: Garment Specs (no artwork keywords — tests 'unclassified') ──
    add_page("GARMENT SPECIFICATIONS", [
        "## Fabric",
        "Composition: 100% Cotton Pique, 220 GSM",
        "Finish: Anti-pilling, moisture wicking",
        "--",
        "## Construction",
        "Fit: Regular Fit",
        "Collar: Ribbed knit collar with 2-button placket",
        "Cuff: Ribbed cuff with side vents",
        "Hem: Tennis tail with side vents",
        "--",
        "## Sizing",
        "Size Range: XS, S, M, L, XL, XXL",
        "Grading: 2cm between sizes",
        "--",
        "## Quality Standards",
        "Wash Test: 40 degree machine wash, 5 cycles",
        "Color Fastness: Grade 4 minimum",
    ])

    # Save
    Path("samples").mkdir(exist_ok=True)
    output = "samples/techpack.pdf"
    pdf.output(output)
    print(f"[OK] Test techpack created: {output}")
    print(f"     Pages: 8 (Cover, 2x Print, Embroidery, Labels, Patches, Packaging, Specs)")
    print(f"\nNow run:")
    print(f"  python main.py analyze samples/techpack.pdf")
    print(f"  python main.py process samples/techpack.pdf -b TestBrand -s SS25-001")


if __name__ == "__main__":
    create_test_techpack()
