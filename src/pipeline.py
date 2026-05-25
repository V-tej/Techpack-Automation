"""
Main Pipeline — Techpack Artwork Automation
=============================================
Orchestrates the full end-to-end workflow:
PDF → Detect → Extract → Split → Name → Upload → Catalog → Approve
"""

from pathlib import Path
from loguru import logger
from datetime import datetime

from src.config import OUTPUT_DIR, ARTWORK_CATEGORIES
from src.pdf_processor import PDFProcessor
from src.naming_engine import (
    NamingEngine, ArtworkEntry, ReportGenerator,
    VendorEntry, UploadLogEntry, ApprovalEntry,
)


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

    # ── Phase 1: PDF Processing + Metadata Extraction ──
    logger.info("Phase 1: Processing PDF with metadata extraction...")
    processor = PDFProcessor()
    result = processor.process_techpack(str(pdf_path), str(output_dir))

    # Use header info to fill style/buyer/season if not provided
    header = result.header_info
    if header:
        if header.style_no and style == "STYLE":
            style = header.style_no
        if header.buyer:
            logger.info("Detected Buyer: {}", header.buyer)
        if header.season:
            logger.info("Detected Season: {}", header.season)

    # ── Phase 1b: Split PDF ──
    logger.info("Phase 1b: Splitting PDF into categories...")
    output_files = processor.split_pdf(str(pdf_path), result)
    logger.info("Split into {} categories", len(output_files))

    # ── Phase 1c: Extract Images ──
    logger.info("Phase 1c: Extracting artwork images...")
    extracted_images = processor.extract_images(str(pdf_path), result)
    logger.info("Extracted {} artwork images", len(extracted_images))

    # ── Phase 2: AI/OCR for unclassified pages ──
    if (use_ai or use_ocr) and result.unclassified_pages:
        logger.info("Phase 2: AI/OCR detection for {} unclassified pages...",
                     len(result.unclassified_pages))
        from src.ai_detector import SmartDetector
        detector = SmartDetector(use_ocr=use_ocr, use_ai=use_ai)
        for page_num in result.unclassified_pages[:]:
            det = detector.detect(str(pdf_path), page_num)
            if det["category"] != "unclassified":
                logger.info("Page {} reclassified → {} (via {})",
                           page_num, det["category"], det["method"])

    # ── Phase 3: Naming & Cataloging ──
    logger.info("Phase 3: Applying naming convention...")
    namer = NamingEngine()
    namer.rename_files(str(output_dir), brand, style)

    # Build full ArtworkEntry records with all 20 fields
    entries = []
    for det in result.detections:
        art_id = namer.generate_id(det.category)

        # Combine Pantone colors into string
        colors_str = ""
        if det.pantone_colors:
            colors_str = ", ".join(
                f"{c['code']} ({c['name']})" if isinstance(c, dict) else str(c)
                for c in det.pantone_colors
            )

        # Combine dimensions into string
        dimensions_str = ", ".join(det.dimensions) if det.dimensions else ""

        # Combine placements into string
        placement_str = ", ".join(det.placements) if det.placements else ""

        # Combine techniques into string
        technique_str = ", ".join(det.techniques) if det.techniques else ""

        # Vendor from page or from BOM extraction
        vendor_str = ", ".join(det.vendors) if det.vendors else ""

        entry = ArtworkEntry(
            artwork_id=art_id,
            style_no=style,
            buyer=header.buyer if header else "",
            season=header.season if header else "",
            garment_type=header.garment_type if header else "",
            artwork_type=det.category,
            artwork_name=det.artwork_name or technique_str,
            placement=placement_str,
            color=colors_str,
            size=dimensions_str,
            file_name=namer.generate_filename(brand, style, det.category),
            vendor=vendor_str,
            status="Pending",
            version="V1",
            techpack_page=det.page_number,
            notes=technique_str,
            confidence=det.confidence,
            detection_method="keyword",
            date_added=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        entries.append(entry)

    # ── Phase 3b: Generate summary report ──
    logger.info("Phase 3b: Generating summary report...")
    report_path = output_dir / "ARTWORK_SUMMARY.md"
    ReportGenerator().generate_summary(entries, str(report_path), header_info=header)

    # ── Phase 4: Google Drive Upload ──
    drive_links = {}
    if upload_to_drive:
        logger.info("Phase 4: Uploading to Google Drive...")
        from src.drive_manager import DriveManager
        drive = DriveManager()
        folder_ids = drive.create_structure(f"{brand}_{style}")
        uploaded = drive.upload_results(str(output_dir), folder_ids)

        # Map links back to entries
        type_links = drive.get_links_by_type(uploaded)
        drive_links = uploaded

        # Update entries with Drive links
        for entry in entries:
            for path, info in uploaded.items():
                if entry.artwork_type in path.lower() or \
                   ARTWORK_CATEGORIES.get(entry.artwork_type, {}).get("folder_name", "") in path:
                    ext = Path(path).suffix.lower()
                    link = info.get("link", "")
                    if ext == ".png":
                        entry.png_link = link
                    elif ext == ".pdf":
                        entry.pdf_link = link

    # ── Phase 5: Update Google Sheets ──
    if update_sheets:
        logger.info("Phase 5: Updating Google Sheets database...")
        from src.naming_engine import SheetsDatabase
        db = SheetsDatabase()

        # Add artwork entries
        db.add_artworks_batch(entries)

        # Add vendors discovered from BOM pages
        if result.all_vendors:
            vendor_entries = []
            for v in result.all_vendors:
                vendor_entries.append(VendorEntry(vendor_name=v))
            db.add_vendors_batch(vendor_entries)

        # Log the upload
        db.log_upload(UploadLogEntry(
            style_no=style,
            uploaded_by="System",
            status="Success",
        ))

        # Create approval records
        approval_entries = []
        for entry in entries:
            approval_entries.append(ApprovalEntry(
                style=style,
                artwork=entry.artwork_id,
                buyer_approval="Pending",
                vendor_approval="Pending",
            ))
        db.add_approvals_batch(approval_entries)

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("Output: {}", output_dir)
    logger.info("Artworks detected: {}", len(entries))
    logger.info("Images extracted: {}", len(extracted_images))
    logger.info("Unclassified pages: {}", len(result.unclassified_pages))
    if header:
        logger.info("Style: {} | Buyer: {} | Season: {}",
                     header.style_no, header.buyer, header.season)
    logger.info("=" * 60)

    return {
        "output_dir": str(output_dir),
        "entries": entries,
        "result": result,
        "header": header,
        "extracted_images": extracted_images,
        "drive_links": drive_links,
    }
