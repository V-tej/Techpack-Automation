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
@click.version_option(version="1.0.0")
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
        title="🤖 Techpack Automation"
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

    # Display results
    table = Table(title="📊 Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Output Directory", result["output_dir"])
    table.add_row("Artworks Detected", str(len(result["entries"])))
    table.add_row("Unclassified Pages", str(len(result["result"].unclassified_pages)))
    console.print(table)


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True))
def analyze(pdf_path):
    """Analyze a techpack PDF without processing."""
    from src.pdf_processor import PDFProcessor
    processor = PDFProcessor()
    pages = processor.extract_text(pdf_path)

    table = Table(title=f"📄 {Path(pdf_path).name}")
    table.add_column("Page", style="cyan", justify="center")
    table.add_column("Text Length", justify="right")
    table.add_column("Images", justify="center")
    table.add_column("Detected Type", style="green")
    table.add_column("Confidence", justify="right")

    for page in pages:
        detections = processor.detect_artwork_type(page["text"])
        if detections:
            best = detections[0]
            det_type = best["category"]
            conf = f"{best['confidence']:.0%}"
        else:
            det_type = "❓ Unknown"
            conf = "-"

        table.add_row(
            str(page["page_number"]),
            str(len(page["text"])),
            "✅" if page["has_images"] else "❌",
            det_type,
            conf,
        )

    console.print(table)


if __name__ == "__main__":
    cli()
