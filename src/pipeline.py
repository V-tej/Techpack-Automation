"""
Main Pipeline — Techpack Artwork Automation
=============================================
Orchestrates the full end-to-end workflow:
PDF → Detect → Split → Name → Upload → Catalog
"""

from pathlib import Path
from loguru import logger
from datetime import datetime

from src.config import OUTPUT_DIR
from src.pdf_processor import PDFProcessor
from src.naming_engine import NamingEngine, ArtworkEntry, ReportGenerator


def process_techpack(
    pdf_path: str,
    brand: str = "BRAND",
    style: str = "STYLE",
    output_dir: str = None,
    upload_to_drive: bool = False,
    use_ai: bool = False,
    use_ocr: bool = False,
    update_sheets: bool = False,
):
    """
    Full end-to-end techpack processing pipeline.

    Args:
        pdf_path: Path to techpack PDF
        brand: Brand name for naming convention
        style: Style code for naming convention
        output_dir: Output directory (default: output/<pdf_name>)
        upload_to_drive: Enable Google Drive upload
        use_ai: Enable AI classification for unclassified pages
        use_ocr: Enable OCR for scanned pages
        update_sheets: Enable Google Sheets database update
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir) if output_dir else OUTPUT_DIR / pdf_path.stem

    logger.info("=" * 60)
    logger.info("TECHPACK AUTOMATION PIPELINE")
    logger.info("PDF: {}", pdf_path.name)
    logger.info("=" * 60)

    # ── Phase 1: PDF Processing ──
    logger.info("Phase 1: Processing PDF...")
    processor = PDFProcessor()
    result = processor.process_techpack(str(pdf_path), str(output_dir))
    output_files = processor.split_pdf(str(pdf_path), result)
    logger.info("Split into {} categories", len(output_files))

    # ── Phase 3: AI/OCR for unclassified pages ──
    if (use_ai or use_ocr) and result.unclassified_pages:
        logger.info("Phase 3: AI/OCR detection for {} unclassified pages...",
                     len(result.unclassified_pages))
        from src.ai_detector import SmartDetector
        detector = SmartDetector(use_ocr=use_ocr, use_ai=use_ai)
        for page_num in result.unclassified_pages[:]:
            det = detector.detect(str(pdf_path), page_num)
            if det["category"] != "unclassified":
                logger.info("Page {} reclassified → {} (via {})",
                           page_num, det["category"], det["method"])

    # ── Phase 4: Naming & Cataloging ──
    logger.info("Phase 4: Applying naming convention...")
    namer = NamingEngine()
    namer.rename_files(str(output_dir), brand, style)

    entries = []
    for det in result.detections:
        art_id = namer.generate_id(det.category)
        entries.append(ArtworkEntry(
            artwork_id=art_id,
            category=det.category,
            confidence=det.confidence,
            detection_method="keyword",
            file_name=f"{brand}_{style}_{det.category}",
            date_added=datetime.now().strftime("%Y-%m-%d %H:%M"),
        ))

    # Generate summary report
    report_path = output_dir / "ARTWORK_SUMMARY.md"
    ReportGenerator().generate_summary(entries, str(report_path))

    # ── Phase 2: Google Drive Upload ──
    if upload_to_drive:
        logger.info("Phase 2: Uploading to Google Drive...")
        from src.drive_manager import DriveManager
        drive = DriveManager()
        folder_ids = drive.create_structure(f"{brand}_{style}")
        drive.upload_results(str(output_dir), folder_ids)

    # ── Phase 4b: Update Google Sheets ──
    if update_sheets:
        logger.info("Phase 4: Updating Google Sheets database...")
        from src.naming_engine import SheetsDatabase
        db = SheetsDatabase()
        db.add_batch(entries)

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("Output: {}", output_dir)
    logger.info("Artworks detected: {}", len(entries))
    logger.info("Unclassified pages: {}", len(result.unclassified_pages))
    logger.info("=" * 60)

    return {"output_dir": str(output_dir), "entries": entries, "result": result}
