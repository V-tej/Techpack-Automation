"""
Phase 4: Naming, Cataloging & Database Engine
=================================================
Handles:
- Standardized naming: BRAND_STYLE_ARTWORKTYPE_VERSION
- Artwork ID generation (ART-001, WL-001, etc.)
- Google Sheets 5-sheet artwork database
- Vendor management
- Approval workflow tracking
- Upload logging
- Summary report generation with color coding
"""

from pathlib import Path
from typing import Optional
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
    SHEETS_CONFIG,
    CATEGORY_COLORS,
    APPROVAL_STATUSES,
    VERSION_STATES,
)


# ============================================
# DATA CLASSES
# ============================================

@dataclass
class ArtworkEntry:
    """Single artwork entry — matches all 20 Artwork_Master columns."""
    artwork_id: str = ""
    style_no: str = ""
    buyer: str = ""
    season: str = ""
    garment_type: str = ""
    artwork_type: str = ""       # category name
    artwork_name: str = ""       # descriptive name (e.g. "Flock Print - Left Chest")
    placement: str = ""
    color: str = ""              # Pantone colors
    size: str = ""               # artwork dimensions
    file_name: str = ""
    png_link: str = ""
    ai_link: str = ""
    pdf_link: str = ""
    dst_link: str = ""
    vendor: str = ""
    status: str = "Pending"
    version: str = "V1"
    techpack_page: int = 0
    notes: str = ""
    # Internal fields (not in Sheets)
    confidence: float = 0.0
    detection_method: str = ""
    date_added: str = ""

    def to_sheet_row(self) -> list:
        """Convert to a list matching Artwork_Master column order."""
        return [
            self.artwork_id,
            self.style_no,
            self.buyer,
            self.season,
            self.garment_type,
            self.artwork_type,
            self.artwork_name,
            self.placement,
            self.color,
            self.size,
            self.file_name,
            self.png_link,
            self.ai_link,
            self.pdf_link,
            self.dst_link,
            self.vendor,
            self.status,
            self.version,
            str(self.techpack_page) if self.techpack_page else "",
            self.notes,
        ]


@dataclass
class VendorEntry:
    """Vendor record for the Vendors sheet."""
    vendor_name: str = ""
    vendor_type: str = ""        # Embroidery, Print, Label, etc.
    contact: str = ""

    def to_sheet_row(self) -> list:
        return [self.vendor_name, self.vendor_type, self.contact]


@dataclass
class UploadLogEntry:
    """Upload log record for the Upload_Log sheet."""
    upload_date: str = ""
    style_no: str = ""
    uploaded_by: str = "System"
    status: str = "Success"

    def to_sheet_row(self) -> list:
        return [
            self.upload_date or datetime.now().strftime("%d-%b-%Y %H:%M"),
            self.style_no,
            self.uploaded_by,
            self.status,
        ]


@dataclass
class ApprovalEntry:
    """Approval record for the Approval_Tracker sheet."""
    style: str = ""
    artwork: str = ""
    buyer_approval: str = "Pending"
    vendor_approval: str = "Pending"

    def to_sheet_row(self) -> list:
        return [self.style, self.artwork, self.buyer_approval, self.vendor_approval]


# ============================================
# NAMING ENGINE
# ============================================

class NamingEngine:
    """Generates standardized file names and artwork IDs."""

    def __init__(self):
        self._counters = {}
        for cat in ARTWORK_CATEGORIES:
            self._counters[cat] = 0

    def generate_id(self, category: str) -> str:
        """Generate sequential artwork ID: ART-001, EMB-001, WL-001, etc."""
        prefix = ARTWORK_CATEGORIES.get(category, {}).get("code_prefix", "UNK")
        self._counters[category] = self._counters.get(category, 0) + 1
        return f"{prefix}-{self._counters[category]:03d}"

    def generate_filename(self, brand: str, style: str, category: str,
                          version: str = None, ext: str = ".pdf") -> str:
        """Generate filename: BRAND_STYLE_TYPE_VERSION.ext"""
        sep = NAMING_SEPARATOR
        ver = version or DEFAULT_VERSION
        folder_name = ARTWORK_CATEGORIES.get(category, {}).get("folder_name", "Unknown")
        name = f"{brand}{sep}{style}{sep}{folder_name}{sep}{ver}{ext}"
        return name.upper().replace(" ", sep)

    def rename_files(self, output_dir: str, brand: str, style: str) -> dict:
        """Rename all output files to standardized naming convention."""
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


# ============================================
# GOOGLE SHEETS 5-SHEET DATABASE
# ============================================

class SheetsDatabase:
    """
    Google Sheets artwork database manager.
    Manages 5 worksheets:
      1. Artwork_Master  — Main artwork catalog (20 columns)
      2. Artwork_Types   — Dropdown master values
      3. Vendors         — Vendor directory
      4. Upload_Log      — Processing history
      5. Approval_Tracker — Approval workflow
    """

    def __init__(self, sheet_id: str = None):
        self.sheet_id = sheet_id or GOOGLE_SHEETS_ID
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_FILE, scopes=GOOGLE_SCOPES
        )
        self.gc = gspread.authorize(creds)
        self.spreadsheet = None
        self.sheets = {}
        self._setup()

    def _setup(self):
        """Initialize all 5 worksheets with headers."""
        try:
            self.spreadsheet = self.gc.open_by_key(self.sheet_id)

            for key, config in SHEETS_CONFIG.items():
                sheet_name = config["name"]
                try:
                    ws = self.spreadsheet.worksheet(sheet_name)
                except gspread.WorksheetNotFound:
                    ws = self.spreadsheet.add_worksheet(sheet_name, rows=1000, cols=25)

                # Set headers if empty
                if not ws.row_values(1):
                    ws.append_row(config["headers"])

                self.sheets[key] = ws

            # Populate Artwork_Types with default values
            self._populate_artwork_types()

            # Apply conditional formatting
            self._apply_formatting()

            logger.info("All 5 sheets initialized successfully")

        except Exception as e:
            logger.error("Sheets setup failed: {}", e)
            raise

    def _populate_artwork_types(self):
        """Populate Artwork_Types sheet with default values if empty."""
        ws = self.sheets.get("artwork_types")
        if ws and len(ws.get_all_values()) <= 1:
            values = SHEETS_CONFIG["artwork_types"]["values"]
            for val in values:
                ws.append_row([val])
            logger.info("Populated Artwork_Types with {} values", len(values))

    def _apply_formatting(self):
        """Apply conditional formatting rules to Artwork_Master."""
        try:
            ws = self.sheets.get("artwork_master")
            if not ws:
                return

            # Conditional formatting for Status column (Q = column 17)
            rules = [
                {
                    "range": "Q:Q",
                    "text": "Approved",
                    "bg": {"red": 0.8, "green": 1.0, "blue": 0.8},
                },
                {
                    "range": "Q:Q",
                    "text": "Pending",
                    "bg": {"red": 1.0, "green": 1.0, "blue": 0.8},
                },
                {
                    "range": "Q:Q",
                    "text": "Rejected",
                    "bg": {"red": 1.0, "green": 0.8, "blue": 0.8},
                },
            ]

            from gspread_formatting import (
                ConditionalFormatRule,
                BooleanCondition,
                BooleanRule,
                CellFormat,
                Color,
                get_conditional_format_rules,
                set_frozen,
            )

            # Freeze header row
            set_frozen(ws, rows=1)

            existing_rules = get_conditional_format_rules(ws)
            for rule_def in rules:
                rule = ConditionalFormatRule(
                    ranges=[rule_def["range"]],
                    booleanRule=BooleanRule(
                        condition=BooleanCondition("TEXT_CONTAINS", [rule_def["text"]]),
                        format=CellFormat(
                            backgroundColor=Color(
                                rule_def["bg"]["red"],
                                rule_def["bg"]["green"],
                                rule_def["bg"]["blue"],
                            )
                        ),
                    ),
                )
                existing_rules.append(rule)

            existing_rules.save()
            logger.info("Applied conditional formatting")

        except ImportError:
            logger.warning("gspread-formatting not installed, skipping conditional formatting")
        except Exception as e:
            logger.warning("Could not apply formatting: {}", e)

    # ── Artwork Master ──────────────────────────────────────────

    def add_artwork(self, entry: ArtworkEntry):
        """Add a single artwork entry to Artwork_Master."""
        ws = self.sheets.get("artwork_master")
        if ws:
            ws.append_row(entry.to_sheet_row())
            logger.info("Added artwork to Sheets: {}", entry.artwork_id)

    def add_artworks_batch(self, entries: list):
        """Add multiple artwork entries to Artwork_Master."""
        ws = self.sheets.get("artwork_master")
        if ws:
            rows = [e.to_sheet_row() for e in entries]
            ws.append_rows(rows)
            logger.info("Added {} artworks to Sheets", len(rows))

    def update_artwork_status(self, artwork_id: str, new_status: str):
        """Update the status of an artwork in Artwork_Master."""
        if new_status not in APPROVAL_STATUSES:
            logger.warning("Invalid status: {}. Must be one of {}", new_status, APPROVAL_STATUSES)
            return

        ws = self.sheets.get("artwork_master")
        if ws:
            cell = ws.find(artwork_id, in_column=1)
            if cell:
                ws.update_cell(cell.row, 17, new_status)  # Column Q = Status
                logger.info("Updated {} status → {}", artwork_id, new_status)
            else:
                logger.warning("Artwork {} not found in Sheets", artwork_id)

    def update_artwork_version(self, artwork_id: str, new_version: str):
        """Update the version of an artwork in Artwork_Master."""
        if new_version not in VERSION_STATES:
            logger.warning("Invalid version: {}. Must be one of {}", new_version, VERSION_STATES)
            return

        ws = self.sheets.get("artwork_master")
        if ws:
            cell = ws.find(artwork_id, in_column=1)
            if cell:
                ws.update_cell(cell.row, 18, new_version)  # Column R = Version
                logger.info("Updated {} version → {}", artwork_id, new_version)
            else:
                logger.warning("Artwork {} not found in Sheets", artwork_id)

    def update_artwork_links(self, artwork_id: str, png_link: str = "",
                             ai_link: str = "", pdf_link: str = "",
                             dst_link: str = ""):
        """Update Google Drive links for an artwork."""
        ws = self.sheets.get("artwork_master")
        if ws:
            cell = ws.find(artwork_id, in_column=1)
            if cell:
                row = cell.row
                if png_link:
                    ws.update_cell(row, 12, png_link)
                if ai_link:
                    ws.update_cell(row, 13, ai_link)
                if pdf_link:
                    ws.update_cell(row, 14, pdf_link)
                if dst_link:
                    ws.update_cell(row, 15, dst_link)
                logger.info("Updated links for {}", artwork_id)

    def get_all_artworks(self) -> list:
        """Get all artwork entries from Artwork_Master."""
        ws = self.sheets.get("artwork_master")
        if ws:
            records = ws.get_all_records()
            return records
        return []

    # ── Vendors ─────────────────────────────────────────────────

    def add_vendor(self, entry: VendorEntry):
        """Add a vendor to the Vendors sheet."""
        ws = self.sheets.get("vendors")
        if ws:
            ws.append_row(entry.to_sheet_row())
            logger.info("Added vendor: {}", entry.vendor_name)

    def add_vendors_batch(self, entries: list):
        """Add multiple vendors to the Vendors sheet."""
        ws = self.sheets.get("vendors")
        if ws:
            # Deduplicate against existing vendors
            existing = ws.col_values(1)
            new_entries = [e for e in entries if e.vendor_name not in existing]
            if new_entries:
                rows = [e.to_sheet_row() for e in new_entries]
                ws.append_rows(rows)
                logger.info("Added {} new vendors", len(rows))

    def get_all_vendors(self) -> list:
        """Get all vendors from the Vendors sheet."""
        ws = self.sheets.get("vendors")
        if ws:
            return ws.get_all_records()
        return []

    # ── Upload Log ──────────────────────────────────────────────

    def log_upload(self, entry: UploadLogEntry):
        """Log an upload to the Upload_Log sheet."""
        ws = self.sheets.get("upload_log")
        if ws:
            ws.append_row(entry.to_sheet_row())
            logger.info("Logged upload: {} - {}", entry.style_no, entry.status)

    # ── Approval Tracker ────────────────────────────────────────

    def add_approval(self, entry: ApprovalEntry):
        """Add an approval record to the Approval_Tracker sheet."""
        ws = self.sheets.get("approval_tracker")
        if ws:
            ws.append_row(entry.to_sheet_row())
            logger.info("Added approval: {} - {}", entry.style, entry.artwork)

    def update_approval(self, style: str, artwork: str,
                        buyer_approval: str = None,
                        vendor_approval: str = None):
        """Update approval status for an artwork."""
        ws = self.sheets.get("approval_tracker")
        if ws:
            # Find the row by style + artwork combination
            all_data = ws.get_all_values()
            for i, row in enumerate(all_data[1:], start=2):  # Skip header
                if len(row) >= 2 and row[0] == style and row[1] == artwork:
                    if buyer_approval:
                        ws.update_cell(i, 3, buyer_approval)
                    if vendor_approval:
                        ws.update_cell(i, 4, vendor_approval)
                    logger.info("Updated approval: {} - {}", style, artwork)
                    return

            logger.warning("Approval record not found: {} - {}", style, artwork)

    def add_approvals_batch(self, entries: list):
        """Add multiple approval records."""
        ws = self.sheets.get("approval_tracker")
        if ws:
            rows = [e.to_sheet_row() for e in entries]
            ws.append_rows(rows)
            logger.info("Added {} approval records", len(rows))

    def get_all_approvals(self) -> list:
        """Get all approval records."""
        ws = self.sheets.get("approval_tracker")
        if ws:
            return ws.get_all_records()
        return []


# ============================================
# REPORT GENERATOR
# ============================================

class ReportGenerator:
    """Generates enhanced artwork summary reports with color coding."""

    # Emoji markers for color coding in Markdown
    CATEGORY_EMOJI = {
        "print": "🔵",
        "embroidery": "🟢",
        "woven_label": "🟠",
        "heat_transfer": "🟣",
        "patch_badge": "🔴",
        "packaging": "🟤",
    }

    def generate_summary(self, entries: list, output_path: str,
                         header_info=None):
        """Generate a comprehensive artwork summary report."""
        output_path = Path(output_path)
        lines = [
            "# 📋 Artwork Summary Report",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"**Total Artworks:** {len(entries)}",
            "",
        ]

        # Header info section
        if header_info:
            lines.extend([
                "## 📝 Techpack Information",
                "",
                f"| Field | Value |",
                f"|---|---|",
                f"| **Style No** | {header_info.style_no} |",
                f"| **Buyer** | {header_info.buyer} |",
                f"| **Season** | {header_info.season} |",
                f"| **Garment Type** | {header_info.garment_type} |",
                f"| **Designer** | {header_info.designer} |",
                f"| **Collection** | {header_info.collection} |",
                f"| **Fabric** | {header_info.fabric} |",
                "",
            ])

        # Color coding legend
        lines.extend([
            "## 🎨 Category Legend",
            "",
        ])
        for cat, info in ARTWORK_CATEGORIES.items():
            emoji = self.CATEGORY_EMOJI.get(cat, "⚪")
            lines.append(f"- {emoji} **{cat.replace('_', ' ').title()}** ({info['color_name']})")
        lines.append("")

        # Full artwork table
        lines.extend([
            "## 📊 Artwork Details",
            "",
            "| # | ID | Type | Artwork Name | Placement | Size | Colors | Technique | Page | Status |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ])

        for i, e in enumerate(entries, 1):
            emoji = self.CATEGORY_EMOJI.get(e.artwork_type, "⚪")
            technique = ""
            if hasattr(e, 'notes') and e.notes:
                technique = e.notes.split("|")[0] if "|" in e.notes else ""

            lines.append(
                f"| {i} | {e.artwork_id} | {emoji} {e.artwork_type} | "
                f"{e.artwork_name} | {e.placement} | {e.size} | "
                f"{e.color} | {technique} | {e.techpack_page} | {e.status} |"
            )

        lines.append("")

        # Category breakdown
        cats = {}
        for e in entries:
            cats[e.artwork_type] = cats.get(e.artwork_type, 0) + 1

        lines.extend([
            "## 📈 Category Breakdown",
            "",
        ])
        for cat, count in sorted(cats.items()):
            emoji = self.CATEGORY_EMOJI.get(cat, "⚪")
            color = CATEGORY_COLORS.get(cat, {}).get("name", "")
            lines.append(f"- {emoji} **{cat.replace('_', ' ').title()}** ({color}): {count} artworks")

        lines.append("")

        # Vendor summary
        vendor_set = set()
        for e in entries:
            if e.vendor:
                vendor_set.add(e.vendor)

        if vendor_set:
            lines.extend([
                "## 🏭 Vendors",
                "",
            ])
            for v in sorted(vendor_set):
                lines.append(f"- {v}")
            lines.append("")

        # Placement diagram (text-based)
        placement_map = {}
        for e in entries:
            if e.placement:
                placement_map[e.placement] = e.artwork_name or e.artwork_id

        if placement_map:
            lines.extend([
                "## 📐 Placement Overview",
                "",
                "```",
                "         ┌──────────────────┐",
                "         │   FRONT VIEW     │",
                "         │                  │",
            ])

            front_placements = {k: v for k, v in placement_map.items()
                                if any(w in k.lower() for w in ["front", "chest", "placket"])}
            back_placements = {k: v for k, v in placement_map.items()
                               if any(w in k.lower() for w in ["back", "cb"])}
            other_placements = {k: v for k, v in placement_map.items()
                                if k not in front_placements and k not in back_placements}

            for placement, name in front_placements.items():
                lines.append(f"         │  ← {placement}: {name}")

            lines.extend([
                "         │                  │",
                "         └──────────────────┘",
                "",
                "         ┌──────────────────┐",
                "         │   BACK VIEW      │",
                "         │                  │",
            ])

            for placement, name in back_placements.items():
                lines.append(f"         │  ← {placement}: {name}")

            lines.extend([
                "         │                  │",
                "         └──────────────────┘",
                "",
            ])

            if other_placements:
                lines.append("**Other Placements:**")
                for placement, name in other_placements.items():
                    lines.append(f"- {placement}: {name}")
                lines.append("")

            lines.append("```")
            lines.append("")

        output_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Report saved: {}", output_path)
