"""
Phase 4: Naming & Cataloging Engine
======================================
Handles:
- Standardized naming: BRAND_STYLE_ARTWORKTYPE_VERSION
- Artwork ID generation (ART-001, WL-001, etc.)
- Google Sheets artwork database
- Summary report generation
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List
from loguru import logger
from dataclasses import dataclass, field
from datetime import datetime

import gspread
from google.oauth2 import service_account

from src.config import (
    GOOGLE_SERVICE_ACCOUNT_FILE,
    GOOGLE_SHEETS_ID,
    GOOGLE_SCOPES,
    ARTWORK_CATEGORIES,
    NAMING_SEPARATOR,
    DEFAULT_VERSION,
)


@dataclass
class ArtworkEntry:
    """Single artwork entry for the catalog database."""
    artwork_id: str
    category: str
    technique: str = ""
    placement: str = ""
    dimensions: str = ""
    pantone_colors: str = ""
    file_name: str = ""
    drive_link: str = ""
    confidence: float = 0.0
    detection_method: str = ""
    date_added: str = ""


class NamingEngine:
    """Generates standardized file names and artwork IDs."""

    def __init__(self):
        self._counters = {}
        for cat, info in ARTWORK_CATEGORIES.items():
            self._counters[cat] = 0

    def generate_id(self, category: str) -> str:
        prefix = ARTWORK_CATEGORIES.get(category, {}).get("code_prefix", "UNK")
        self._counters[category] = self._counters.get(category, 0) + 1
        return f"{prefix}-{self._counters[category]:03d}"

    def generate_filename(self, brand: str, style: str, category: str,
                          version: str = None, ext: str = ".pdf") -> str:
        sep = NAMING_SEPARATOR
        ver = version or DEFAULT_VERSION
        folder_name = ARTWORK_CATEGORIES.get(category, {}).get("folder_name", "Unknown")
        name = f"{brand}{sep}{style}{sep}{folder_name}{sep}{ver}{ext}"
        return name.upper().replace(" ", sep)

    def rename_files(self, output_dir: str, brand: str, style: str) -> dict:
        output_dir = Path(output_dir)
        renamed = {}
        for cat, info in ARTWORK_CATEGORIES.items():
            cat_dir = output_dir / info["folder_name"]
            if not cat_dir.exists():
                continue
            for fp in cat_dir.glob("*"):
                if fp.is_file() and not fp.name.startswith("."):
                    new_name = self.generate_filename(brand, style, cat, ext=fp.suffix)
                    new_path = fp.parent / new_name
                    fp.replace(new_path)
                    renamed[str(fp)] = str(new_path)
                    logger.info("Renamed: {} → {}", fp.name, new_name)
        return renamed


class SheetsDatabase:
    """Google Sheets artwork database manager."""

    HEADERS = [
        "Artwork ID", "Category", "Technique", "Placement",
        "Dimensions", "Pantone Colors", "File Name",
        "Drive Link", "Confidence", "Detection Method", "Date Added"
    ]

    def __init__(self, sheet_id: str = None):
        self.sheet_id = sheet_id or GOOGLE_SHEETS_ID
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE, scopes=GOOGLE_SCOPES
        )
        self.gc = gspread.authorize(creds)
        self.sheet = None
        self._setup()

    def _setup(self):
        try:
            spreadsheet = self.gc.open_by_key(self.sheet_id)
            try:
                self.sheet = spreadsheet.worksheet("Artwork Database")
            except gspread.WorksheetNotFound:
                self.sheet = spreadsheet.add_worksheet("Artwork Database", rows=1000, cols=20)
            if not self.sheet.row_values(1):
                self.sheet.append_row(self.HEADERS)
            logger.info("Sheets database ready")
        except Exception as e:
            logger.error("Sheets setup failed: {}", e)
            raise

    def add_entry(self, entry: ArtworkEntry):
        row = [
            entry.artwork_id, entry.category, entry.technique,
            entry.placement, entry.dimensions, entry.pantone_colors,
            entry.file_name, entry.drive_link,
            str(entry.confidence), entry.detection_method,
            entry.date_added or datetime.now().strftime("%Y-%m-%d %H:%M"),
        ]
        self.sheet.append_row(row)
        logger.info("Added to Sheets: {}", entry.artwork_id)

    def add_batch(self, entries: list[ArtworkEntry]):
        rows = []
        for e in entries:
            rows.append([
                e.artwork_id, e.category, e.technique, e.placement,
                e.dimensions, e.pantone_colors, e.file_name, e.drive_link,
                str(e.confidence), e.detection_method,
                e.date_added or datetime.now().strftime("%Y-%m-%d %H:%M"),
            ])
        self.sheet.append_rows(rows)
        logger.info("Added {} entries to Sheets", len(rows))


class ReportGenerator:
    """Generates artwork summary reports."""

    def generate_summary(self, entries: list[ArtworkEntry], output_path: str):
        output_path = Path(output_path)
        lines = [
            "# Artwork Summary Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Total Artworks: {len(entries)}", "",
            "| ID | Category | Technique | Placement | Colors | Confidence |",
            "|---|---|---|---|---|---|",
        ]
        for e in entries:
            lines.append(
                f"| {e.artwork_id} | {e.category} | {e.technique} | "
                f"{e.placement} | {e.pantone_colors} | {e.confidence:.0%} |"
            )
        lines.append("")
        cats = {}
        for e in entries:
            cats[e.category] = cats.get(e.category, 0) + 1
        lines.append("## Category Breakdown")
        for cat, count in sorted(cats.items()):
            lines.append(f"- **{cat}**: {count} artworks")

        output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Report saved: {}", output_path)
