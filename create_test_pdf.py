"""Generate a sample techpack PDF for testing the automation system.
Uses fpdf2 (pure Python, no DLL issues).
Updated to match real client techpack format patterns.
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

    # ── Page 1: Cover / Design Sheet (matches real format) ──
    pdf.add_page()
    pdf.set_font("Helvetica", style="B", size=14)
    pdf.set_text_color(30, 30, 30)

    # Header table-like format (matching SP26KB063 style)
    headers = [
        "DEPT: BOYS-KB",
        "STYLE NO  :TB-SS25-001",
        "COLLECTION  :MAIN LINE",
        "BUYER: ZARA",
        "DESIGNER: AMIT/SARAH",
        "SEASON:SPRING 26",
    ]
    for h in headers:
        pdf.cell(0, 8, h, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.set_font("Helvetica", style="B", size=18)
    pdf.cell(0, 12, "DESIGN SHEET", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", size=12)
    design_info = [
        "STYLE DESCRIPTION",
        "",
        "FASHION PRINTED POLO TEE",
        "",
        "FABRIC:",
        "TOP: 95% COTTON 5% ELASTANE, 220 GSM",
        "BOTTOM: 100% COTTON PIQUE",
        "",
        "17-1349 TCX",
        "EXUBERANCE",
        "11-0601 TCX",
        "BRIGHT WHITE",
        "19-3911 TCX",
        "BLACK BEAUTY",
        "",
        "POLO FIT TO BE FOLLOWED AS SAMPLE",
        "DATE: 21-05-24",
    ]
    for line in design_info:
        pdf.cell(0, 7, line, new_x="LMARGIN", new_y="NEXT")

    # ── Page 2: Working Sketch / Spec Detail ──
    add_page("SPEC DETAIL", [
        "## Construction Details",
        "BRANDED STRETCH TAPE PATCH AT INNER NECK",
        "FLOCK PRINT on front panel",
        "1/8TH WHITE PIPING SILICON BRANDING",
        "MOON PATCH INSIDE",
        "1/8\" DN FLATLOCK STITCH",
        "BRANDING LABEL at hem",
        "CURVED HEM",
        "--",
        "## Artwork Callouts",
        "PUFFED EMBROIDERY at left chest",
        "HD PRINT at center back",
        "HEAT TRANSFER LABEL",
        "( MAIN LABEL - SIZE/ CONTENT/ WASHCARE)",
        "--",
        "17-1349 TCX",
        "EXUBERANCE",
        "12-4705 TCX",
        "BLUE BLUSH",
        "--",
        "DOUBLE LAYER COLOR NEEDED",
        "RIB HT 1.2 CM",
        "11 cm FROM SHOULDER EDGE",
        "0.8 CM HT TAPE IN FABRIC",
    ])

    # ── Page 3: Artwork Detail ──
    add_page("ARTWORK DETAIL", [
        "## Print Artwork",
        "TECHNIQUE:SCREEN PRINT AS SAMPLE",
        "SOLID 2 MM HD PRINT",
        "FLOCK PRINT on chest",
        "--",
        "## Placement & Dimensions",
        "PLACEMENT: LEFT CHEST",
        "WIDTH:3 CM",
        "HEIGHT:2.7 CM",
        "11 INCHES WIDTH (back print)",
        "8 CM WIDTH (sleeve)",
        "--",
        "## Embroidery",
        "TECHNIQUE:EMBROIDERY IN COTTON POLY THREAD",
        "TUFT EMBROIDERY at sleeve",
        "COLOR FOLLOW AS SAMPLE",
        "--",
        "PRINT ARTWORK",
        "BASE FABRIC PRINT COL 2 PRINT COL 1",
    ])

    # ── Page 4: Embroidery Detail ──
    add_page("ARTWORK: SLEEVE EMBROIDERY", [
        "## Artwork Type",
        "Technique: Flat Embroidery",
        "Process: Satin Stitch + 3D Puff Embroidery",
        "--",
        "## Placement & Dimensions",
        "Placement: Right Sleeve",
        "Dimensions: 5 CM x 3 CM",
        "--",
        "## Thread Specifications",
        "Thread: Madeira 1147 (Navy), Madeira 1001 (White)",
        "Stitch Count: approx 8,500 stitches",
        "Backing: Cut-away backing required",
        "--",
        "17-1349 TCX",
        "EXUBERANCE",
        "--",
        "3D puff on lettering only. Flat embroidery on icon.",
        "Embroidered patch sewn onto garment after production.",
    ])

    # ── Page 5: Labels & Trims ──
    add_page("WOVEN LABEL SPECIFICATIONS", [
        "## Main Label",
        "Type: Damask Woven Label",
        "Size: 4 CM x 2 CM",
        "Placement: INNER NECK - Center Back",
        "Colors: Navy + White thread",
        "--",
        "## Heat Transfer Label",
        "HEAT TRANSFER AT INNER YOKE",
        "SILICON LABEL with 3 mm raised HT",
        "Stitching depression detail",
        "4 CM WIDTH",
        "--",
        "## Flag Label",
        "BRANDING LABEL AT HEM",
        "Satine + Twill Dobby Label",
        "4 cm X 2.8 cm",
        "at side seam, 7cm above hem",
        "--",
        "## Washcare Label",
        "WASHCARE LABEL",
        "MATERIAL SATIN",
        "ADD COUNTRY OF ORIGIN",
        "INSERT IN SIDE SEAM",
    ])

    # ── Page 6: Patches & Badges ──
    add_page("PATCH & BADGE DETAILS", [
        "## Item 1: Silicone Badge",
        "Material: SILICONE BADGE - 3D molded rubber",
        "Placement: Left Sleeve",
        "Dimensions: 4 CM x 4 CM",
        "Colors: Navy + White",
        "--",
        "## Item 2: Leather Patch",
        "Material: PU Leather with deboss logo",
        "Placement: Hem - Right Side",
        "Dimensions: 6 CM x 3 CM",
        "Attachment: TPU patch backing, heat seal",
        "--",
        "## Item 3: Branding Badge",
        "BRANDING BADGE at outer CB neck",
        "Poly/elastane with stretch silicon print",
    ])

    # ── Page 7: BOM (Bill of Materials) ──
    add_page("BILL OF MATERIALS", [
        "## Body Fabric",
        "DESCRIPTION CONTENT/FINISH PLACEMENT CONSUMPTION SOURCE",
        "Body- 95% Cotton/5% spandex, 220gsm, Bio+Silicon",
        "Neck rib - 1x1 rib, 95/5 ctn/spdx",
        "",
        "## Trims",
        "Hang tag - 10x6.5 cms, paper 350gsm, UV print",
        "tbc Avery Dennison",
        "",
        "Thread- spun poly 80's TKT, dtm, spi-12",
        "DTM body all over tbc vardhamann/coats",
        "",
        "Mobilon stretch transparent tape 10 mm",
        "at shoulder seam tbc factory",
        "",
        "## Packaging",
        "Tissue paper packing tbc factory",
        "BOPP Self seal poly cover transparent 27x32cm packing tbc factory",
        "Packing tape 4 inch transparent printed factory",
        "Carton box 5 ply virgin paper factory",
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
    print(f"     Pages: 8")
    print(f"     Page 1: Design Sheet (Style/Buyer/Season/Pantone colors)")
    print(f"     Page 2: Spec Detail (flock print, embroidery, heat transfer)")
    print(f"     Page 3: Artwork Detail (screen print, HD print, dimensions)")
    print(f"     Page 4: Embroidery Detail (3D puff, satin stitch)")
    print(f"     Page 5: Labels (woven label, heat transfer, washcare)")
    print(f"     Page 6: Patches/Badges (silicone, leather, branding)")
    print(f"     Page 7: BOM (Avery Dennison, vardhamann/coats)")
    print(f"     Page 8: Garment Specs (unclassified)")
    print(f"\nNow run:")
    print(f"  python main.py analyze samples/techpack.pdf")
    print(f"  python main.py process samples/techpack.pdf -b TestBrand -s TB-SS25-001")


if __name__ == "__main__":
    create_test_techpack()
