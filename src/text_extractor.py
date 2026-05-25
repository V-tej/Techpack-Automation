"""
Text Extraction Engine
========================
Extracts structured metadata from techpack PDF text:
- Header info (style, buyer, season, garment type, designer)
- Pantone color references
- Dimensions and sizes
- Placement callouts
- Production techniques
- Vendor/source information
- Artwork names

Patterns are derived from real client techpack samples:
  - HD-SS-WT-07 WOMENS TEE (Harley-Davidson)
  - SP26KB063 (Boys Polo & Shorts Set)
"""

import re
from typing import Optional
from dataclasses import dataclass, field
from loguru import logger

from src.config import (
    PANTONE_PATTERN,
    DIMENSION_PATTERNS,
    PLACEMENT_KEYWORDS,
    TECHNIQUE_KEYWORDS,
    HEADER_PATTERNS,
)


@dataclass
class HeaderInfo:
    """Structured header metadata extracted from techpack Page 1."""
    style_no: str = ""
    buyer: str = ""
    season: str = ""
    garment_type: str = ""
    designer: str = ""
    collection: str = ""
    fabric: str = ""
    date: str = ""


@dataclass
class ArtworkMetadata:
    """Structured artwork metadata extracted from a techpack page."""
    techniques: list = field(default_factory=list)
    placements: list = field(default_factory=list)
    dimensions: list = field(default_factory=list)
    pantone_colors: list = field(default_factory=list)
    vendors: list = field(default_factory=list)
    artwork_name: str = ""
    raw_text: str = ""


class TextExtractor:
    """Extracts structured data from techpack PDF text using regex patterns."""

    def __init__(self):
        logger.info("TextExtractor initialized")

    # ── Header Extraction (Page 1) ──────────────────────────────

    def extract_header(self, text: str) -> HeaderInfo:
        """
        Extract header info from the first page of a techpack.

        Handles formats like:
          STYLE NO  :SP26KB063
          BUYER: mOHIT
          SEASON:SPRING 26
          HD-SS-WT-07- REG 2024 IMPULSE
          AUTUMN WINTER 2024-25
        """
        header = HeaderInfo()
        text_upper = text.upper()

        # Style No
        for pattern in HEADER_PATTERNS["style_no"]:
            match = re.search(pattern, text_upper)
            if match:
                header.style_no = match.group(1).strip()
                break

        # Buyer
        for pattern in HEADER_PATTERNS["buyer"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                header.buyer = match.group(1).strip().title()
                break

        # Season
        for pattern in HEADER_PATTERNS["season"]:
            match = re.search(pattern, text_upper)
            if match:
                header.season = match.group(1).strip().title()
                break

        # Garment Type
        for pattern in HEADER_PATTERNS["garment_type"]:
            match = re.search(pattern, text_upper)
            if match:
                header.garment_type = match.group(1).strip().title()
                break

        # Designer
        for pattern in HEADER_PATTERNS["designer"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                header.designer = match.group(1).strip().title()
                break

        # Collection
        for pattern in HEADER_PATTERNS["collection"]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                header.collection = match.group(1).strip().title()
                break

        # Fabric
        for pattern in HEADER_PATTERNS["fabric"]:
            match = re.search(pattern, text_upper)
            if match:
                header.fabric = match.group(1).strip().title()
                break

        # Date — common formats: 21-05-24, 2024-05-21
        date_match = re.search(r'(\d{2}-\d{2}-\d{2,4})', text)
        if date_match:
            header.date = date_match.group(1)

        logger.info(
            "Header extracted — Style: {}, Buyer: {}, Season: {}, Garment: {}",
            header.style_no, header.buyer, header.season, header.garment_type
        )
        return header

    # ── Pantone Color Extraction ────────────────────────────────

    def extract_pantone_colors(self, text: str) -> list:
        """
        Extract Pantone TCX color references.

        Handles formats like:
          17-1349 TCX
          EXUBERANCE
          11-0601 TCX
          BRIGHT WHITE
        """
        colors = []
        matches = re.finditer(PANTONE_PATTERN, text, re.IGNORECASE)
        for match in matches:
            code = match.group(1).strip()
            name = match.group(2).strip()
            colors.append({"code": f"{code} TCX", "name": name})

        if colors:
            logger.debug("Found {} Pantone colors", len(colors))
        return colors

    # ── Dimension Extraction ────────────────────────────────────

    def extract_dimensions(self, text: str) -> list:
        """
        Extract artwork dimensions.

        Handles formats like:
          11 INCHES WIDTH
          8 CM WIDTH
          WIDTH:3 CM
          HEIGHT:2.7 CM
          4 CM X 2.8 CM
          5 CM
        """
        dimensions = []
        text_upper = text.upper()

        for pattern in DIMENSION_PATTERNS:
            matches = re.finditer(pattern, text_upper)
            for match in matches:
                groups = match.groups()
                raw = match.group(0).strip()
                if len(groups) == 2:
                    dimensions.append(f"{groups[0]} x {groups[1]} cm")
                else:
                    dimensions.append(raw)

        # Deduplicate
        seen = set()
        unique = []
        for d in dimensions:
            normalized = d.lower().replace(" ", "")
            if normalized not in seen:
                seen.add(normalized)
                unique.append(d)

        if unique:
            logger.debug("Found {} dimensions: {}", len(unique), unique)
        return unique

    # ── Placement Extraction ────────────────────────────────────

    def extract_placements(self, text: str) -> list:
        """
        Detect placement callouts.

        Handles: LEFT CHEST, INNER NECK, INNER YOKE, AT HEM, etc.
        """
        placements = []
        text_lower = text.lower()

        for keyword in PLACEMENT_KEYWORDS:
            if keyword in text_lower:
                placements.append(keyword.title())

        if placements:
            logger.debug("Found placements: {}", placements)
        return placements

    # ── Technique Extraction ────────────────────────────────────

    def extract_techniques(self, text: str) -> list:
        """
        Identify production techniques mentioned in text.

        Handles: SCREEN PRINT, FLOCK PRINT, PUFFED EMBROIDERY, etc.
        """
        techniques = []
        text_lower = text.lower()

        for keyword in TECHNIQUE_KEYWORDS:
            if keyword in text_lower:
                techniques.append(keyword.title())

        if techniques:
            logger.debug("Found techniques: {}", techniques)
        return techniques

    # ── Vendor Extraction ───────────────────────────────────────

    def extract_vendors(self, text: str) -> list:
        """
        Extract vendor/source names from BOM pages.

        Handles: Avery Dennison, vardhamann/coats, factory, etc.
        """
        vendors = []
        # Common vendor patterns in BOM
        vendor_patterns = [
            r'(?:SOURCE|VENDOR|SUPPLIER)\s*[:\-]?\s*([A-Za-z\s\/\.]+?)(?:\n|$)',
            r'(Avery\s+Dennison)',
            r'(vardhamann[\w\/]*)',
            r'(coats)',
        ]

        for pattern in vendor_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                vendor = match.group(1).strip().title()
                if vendor.lower() not in ['factory', 'tbc', '']:
                    vendors.append(vendor)

        # Deduplicate
        vendors = list(dict.fromkeys(vendors))

        if vendors:
            logger.debug("Found vendors: {}", vendors)
        return vendors

    # ── Full Page Metadata Extraction ───────────────────────────

    def extract_page_metadata(self, text: str) -> ArtworkMetadata:
        """
        Extract all structured metadata from a single techpack page.
        """
        metadata = ArtworkMetadata(
            techniques=self.extract_techniques(text),
            placements=self.extract_placements(text),
            dimensions=self.extract_dimensions(text),
            pantone_colors=self.extract_pantone_colors(text),
            vendors=self.extract_vendors(text),
            raw_text=text[:500],
        )

        # Generate artwork name from technique + placement
        metadata.artwork_name = self._generate_artwork_name(
            metadata.techniques, metadata.placements
        )

        return metadata

    # ── Artwork Name Generation ─────────────────────────────────

    def _generate_artwork_name(self, techniques: list, placements: list) -> str:
        """
        Generate a descriptive artwork name from detected technique + placement.
        Example: "Flock Print - Left Chest"
        """
        parts = []
        if techniques:
            parts.append(techniques[0])
        if placements:
            parts.append(placements[0])

        return " - ".join(parts) if parts else ""

    # ── BOM Detection ───────────────────────────────────────────

    def is_bom_page(self, text: str) -> bool:
        """Check if a page is a Bill of Materials page."""
        text_upper = text.upper()
        bom_keywords = [
            "BILL OF MATERIALS", "BOM", "DESCRIPTION CONTENT",
            "PLACEMENT CONSUMPTION SOURCE",
        ]
        return any(kw in text_upper for kw in bom_keywords)

    def is_spec_page(self, text: str) -> bool:
        """Check if a page is a specification/measurement page."""
        text_upper = text.upper()
        spec_keywords = [
            "SPEC SHEET", "MEASUREMENT", "GRADING", "SIZE CHART",
            "SPEC DETAIL",
        ]
        return any(kw in text_upper for kw in spec_keywords)

    def is_artwork_page(self, text: str) -> bool:
        """Check if a page is specifically an artwork detail page."""
        text_upper = text.upper()
        artwork_keywords = [
            "ARTWORK DETAIL", "ARTWORK SPECIFICATION",
            "PRINT ARTWORK", "EMBROIDERY ARTWORK",
        ]
        return any(kw in text_upper for kw in artwork_keywords)
