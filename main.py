"""
CLI Entry Point — Techpack Artwork Automation
================================================
Command-line interface using Click.
"""

import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.group()
@click.version_option(version="2.0.0")
def cli():
    """🤖 Techpack Artwork Automation System"""
    pass


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("--brand", "-b", default="BRAND", help="Brand name")
@click.option("--style", "-s", default="STYLE", help="Style code")
@click.option("--output", "-o", default=None, help="Output directory")
@click.option("--drive", is_flag=True, help="Upload to Google Drive")
@click.option("--ai", is_flag=True, help="Enable AI detection")
@click.option("--ocr", is_flag=True, help="Enable OCR detection")
@click.option("--sheets", is_flag=True, help="Update Google Sheets")
def process(pdf_path, brand, style, output, drive, ai, ocr, sheets):
    """Process a techpack PDF end-to-end."""
    console.print(Panel.fit(
        f"[bold cyan]Processing:[/] {Path(pdf_path).name}\n"
        f"[bold]Brand:[/] {brand} | [bold]Style:[/] {style}",
        title="🤖 Techpack Automation v2.0"
    ))

    from src.pipeline import process_techpack
    result = process_techpack(
        pdf_path=pdf_path,
        brand=brand,
        style=style,
        output_dir=output,
        upload_to_drive=drive,
        use_ai=ai,
        use_ocr=ocr,
        update_sheets=sheets,
    )

    # Header info
    header = result.get("header")
    if header and header.style_no:
        info_table = Table(title="📝 Detected Techpack Info")
        info_table.add_column("Field", style="cyan")
        info_table.add_column("Value", style="green")
        info_table.add_row("Style No", header.style_no)
        info_table.add_row("Buyer", header.buyer)
        info_table.add_row("Season", header.season)
        info_table.add_row("Garment Type", header.garment_type)
        info_table.add_row("Designer", header.designer)
        info_table.add_row("Fabric", header.fabric)
        console.print(info_table)

    # Summary stats
    stats_table = Table(title="📊 Processing Results")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="green")
    stats_table.add_row("Output Directory", result["output_dir"])
    stats_table.add_row("Artworks Detected", str(len(result["entries"])))
    stats_table.add_row("Images Extracted", str(len(result.get("extracted_images", []))))
    stats_table.add_row("Unclassified Pages", str(len(result["result"].unclassified_pages)))
    console.print(stats_table)

    # Detailed artwork table
    if result["entries"]:
        art_table = Table(title="🎨 Artwork Details")
        art_table.add_column("ID", style="bold")
        art_table.add_column("Type", style="cyan")
        art_table.add_column("Name")
        art_table.add_column("Placement")
        art_table.add_column("Size")
        art_table.add_column("Colors")
        art_table.add_column("Page", justify="center")
        art_table.add_column("Confidence", justify="right")

        for e in result["entries"]:
            colors_short = e.color[:30] + "..." if len(e.color) > 30 else e.color
            art_table.add_row(
                e.artwork_id,
                e.artwork_type,
                e.artwork_name or "—",
                e.placement or "—",
                e.size or "—",
                colors_short or "—",
                str(e.techpack_page),
                f"{e.confidence:.0%}",
            )
        console.print(art_table)

    # Vendors
    all_vendors = result["result"].all_vendors
    if all_vendors:
        console.print(f"\n🏭 [bold]Vendors detected:[/] {', '.join(all_vendors)}")


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
def analyze(pdf_path):
    """Analyze a techpack PDF without processing."""
    from src.pdf_processor import PDFProcessor
    processor = PDFProcessor()
    pages = processor.extract_text(pdf_path)

    # Extract header from page 1
    header = processor.text_extractor.extract_header(pages[0]["text"]) if pages else None

    if header and header.style_no:
        console.print(Panel.fit(
            f"[bold]Style:[/] {header.style_no} | "
            f"[bold]Buyer:[/] {header.buyer} | "
            f"[bold]Season:[/] {header.season}",
            title="📝 Techpack Info"
        ))

    table = Table(title=f"📄 {Path(pdf_path).name}")
    table.add_column("Page", style="cyan", justify="center")
    table.add_column("Text", justify="right")
    table.add_column("Images", justify="center")
    table.add_column("Type", style="green")
    table.add_column("Confidence", justify="right")
    table.add_column("Techniques")
    table.add_column("Placements")
    table.add_column("Colors")

    for page in pages:
        detections = processor.detect_artwork_type(page["text"])
        metadata = processor.text_extractor.extract_page_metadata(page["text"])

        if detections:
            best = detections[0]
            det_type = best["category"]
            conf = f"{best['confidence']:.0%}"
        else:
            det_type = "❓ Unknown"
            conf = "-"

        techniques = ", ".join(metadata.techniques[:2]) if metadata.techniques else "—"
        placements = ", ".join(metadata.placements[:2]) if metadata.placements else "—"
        colors = ", ".join(
            c["code"] for c in metadata.pantone_colors[:2]
        ) if metadata.pantone_colors else "—"

        table.add_row(
            str(page["page_number"]),
            str(len(page["text"])),
            "✅" if page["has_images"] else "❌",
            det_type,
            conf,
            techniques,
            placements,
            colors,
        )

    console.print(table)


if __name__ == "__main__":
    cli()
