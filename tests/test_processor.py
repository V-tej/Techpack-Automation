"""
Tests for Techpack Automation System
======================================
Tests cover:
- Keyword-based artwork type detection
- Naming convention generation
- Text extraction (Pantone colors, dimensions, placements, techniques)
- Header info extraction (style, buyer, season)
- Real techpack text patterns from client samples
"""
import pytest
from pathlib import Path
from src.pdf_processor import PDFProcessor, ArtworkDetection
from src.text_extractor import TextExtractor, HeaderInfo


class TestKeywordDetection:
    """Test keyword-based artwork type detection."""

    def setup_method(self):
        self.processor = PDFProcessor()

    def test_detect_print(self):
        text = "Front chest screen print artwork - DTF sublimation"
        results = self.processor.detect_artwork_type(text)
        assert len(results) > 0
        assert results[0]["category"] == "print"

    def test_detect_embroidery(self):
        text = "Left chest embroidery design - 3D puff embroidered logo"
        results = self.processor.detect_artwork_type(text)
        assert len(results) > 0
        assert results[0]["category"] == "embroidery"

    def test_detect_woven_label(self):
        text = "Main label - woven label design for neck"
        results = self.processor.detect_artwork_type(text)
        assert len(results) > 0
        assert results[0]["category"] == "woven_label"

    def test_detect_patch(self):
        text = "Rubber patch design - silicone badge for sleeve"
        results = self.processor.detect_artwork_type(text)
        assert len(results) > 0
        assert results[0]["category"] == "patch_badge"

    def test_detect_heat_transfer(self):
        text = "HEAT TRANSFER LABEL at inner yoke"
        results = self.processor.detect_artwork_type(text)
        assert len(results) > 0
        assert results[0]["category"] == "heat_transfer"

    def test_detect_packaging(self):
        text = "Hangtag design - polybag sticker with barcode"
        results = self.processor.detect_artwork_type(text)
        assert len(results) > 0
        assert results[0]["category"] == "packaging"

    def test_no_detection(self):
        text = "General specifications and measurements"
        results = self.processor.detect_artwork_type(text)
        assert len(results) == 0

    def test_multiple_detections(self):
        text = "Print artwork with embroidery detail and woven label"
        results = self.processor.detect_artwork_type(text)
        assert len(results) >= 2

    def test_confidence_scoring(self):
        text = "screen print dtf sublimation digital print pigment print"
        results = self.processor.detect_artwork_type(text)
        assert results[0]["confidence"] > 0.5


class TestKeywordDetectionRealSamples:
    """Test keyword detection with real client techpack text patterns."""

    def setup_method(self):
        self.processor = PDFProcessor()

    def test_harley_page2_flock_print(self):
        text = """FLOCK PRINT
        1/8TH WHITE PIPING SILICON BRANDING
        MOON PATCH INSIDE
        BRANDING LABEL
        HEAT TRANSFER LABEL"""
        results = self.processor.detect_artwork_type(text)
        assert len(results) > 0
        categories = [r["category"] for r in results]
        assert "print" in categories

    def test_harley_page3_hd_print(self):
        text = """SOLID 2 MM HD PRINT
        TUFT EMBROIDERY
        PRINT ARTWORK
        FLOCK PRINT"""
        results = self.processor.detect_artwork_type(text)
        categories = [r["category"] for r in results]
        assert "print" in categories
        assert "embroidery" in categories

    def test_harley_page4_labels(self):
        text = """HEAT TRANSFER AT INNER YOKE
        BRANDING LABEL AT HEM
        SILICON LABEL
        3 mm raised HT"""
        results = self.processor.detect_artwork_type(text)
        categories = [r["category"] for r in results]
        assert "heat_transfer" in categories or "woven_label" in categories

    def test_sp26_artwork_detail(self):
        text = """ARTWORK DETAIL
        TECHNIQUE:SCREEN PRINT AS SAMPLE
        TECHNIQUE:EMBROIDERY IN COTTON POLY THREAD
        COLOR FOLLOW AS SAMPLE
        PLACEMENT AS PER SKETCH"""
        results = self.processor.detect_artwork_type(text)
        categories = [r["category"] for r in results]
        assert "print" in categories
        assert "embroidery" in categories

    def test_sp26_labels(self):
        text = """CODE : PWT
        PARTY TAG
        CODE : PWLL
        PARTY WEAR WOVEN LOOP LABEL"""
        results = self.processor.detect_artwork_type(text)
        assert len(results) > 0


class TestNamingEngine:
    """Test naming convention generation."""

    def test_generate_id(self):
        from src.naming_engine import NamingEngine
        namer = NamingEngine()
        id1 = namer.generate_id("print")
        id2 = namer.generate_id("print")
        assert id1 == "ART-001"
        assert id2 == "ART-002"

    def test_generate_id_embroidery(self):
        from src.naming_engine import NamingEngine
        namer = NamingEngine()
        id1 = namer.generate_id("embroidery")
        assert id1 == "EMB-001"

    def test_generate_id_woven_label(self):
        from src.naming_engine import NamingEngine
        namer = NamingEngine()
        id1 = namer.generate_id("woven_label")
        assert id1 == "WL-001"

    def test_generate_id_patch_badge(self):
        from src.naming_engine import NamingEngine
        namer = NamingEngine()
        id1 = namer.generate_id("patch_badge")
        assert id1 == "SB-001"

    def test_generate_filename(self):
        from src.naming_engine import NamingEngine
        namer = NamingEngine()
        name = namer.generate_filename("NIKE", "SS25-001", "print")
        assert "NIKE" in name
        assert "SS25-001" in name
        assert "PRINTS" in name

    def test_generate_filename_version(self):
        from src.naming_engine import NamingEngine
        namer = NamingEngine()
        name = namer.generate_filename("HD", "WT-07", "embroidery", version="V2")
        assert "V2" in name
        assert "EMBROIDERY" in name


class TestTextExtractor:
    """Test text extraction engine."""

    def setup_method(self):
        self.extractor = TextExtractor()

    # ── Pantone Color Tests ──

    def test_extract_pantone_colors(self):
        text = """17-1349 TCX
EXUBERANCE
11-0601 TCX
BRIGHT WHITE"""
        colors = self.extractor.extract_pantone_colors(text)
        assert len(colors) >= 2
        codes = [c["code"] for c in colors]
        assert "17-1349 TCX" in codes
        assert "11-0601 TCX" in codes

    def test_extract_pantone_color_names(self):
        text = """19-3911 TCX
BLACK BEAUTY"""
        colors = self.extractor.extract_pantone_colors(text)
        assert len(colors) >= 1
        assert colors[0]["name"] == "BLACK BEAUTY"

    # ── Dimension Tests ──

    def test_extract_dimensions_cm(self):
        text = "WIDTH:3 CM\nHEIGHT:2.7 CM"
        dims = self.extractor.extract_dimensions(text)
        assert len(dims) >= 1

    def test_extract_dimensions_inches(self):
        text = "11 INCHES WIDTH"
        dims = self.extractor.extract_dimensions(text)
        assert len(dims) >= 1

    def test_extract_dimensions_combined(self):
        text = "4 CM X 2.8 CM"
        dims = self.extractor.extract_dimensions(text)
        assert len(dims) >= 1

    # ── Placement Tests ──

    def test_extract_placements(self):
        text = "LEFT CHEST placement, INNER NECK area, AT HEM"
        placements = self.extractor.extract_placements(text)
        assert "Left Chest" in placements
        assert "Inner Neck" in placements

    def test_extract_placement_inner_yoke(self):
        text = "HEAT TRANSFER AT INNER YOKE"
        placements = self.extractor.extract_placements(text)
        assert "Inner Yoke" in placements

    # ── Technique Tests ──

    def test_extract_techniques_print(self):
        text = "TECHNIQUE:SCREEN PRINT AS SAMPLE"
        techniques = self.extractor.extract_techniques(text)
        assert "Screen Print" in techniques

    def test_extract_techniques_embroidery(self):
        text = "PUFFED EMBROIDERY on left chest"
        techniques = self.extractor.extract_techniques(text)
        assert "Puffed Embroidery" in techniques

    def test_extract_techniques_multiple(self):
        text = "HD PRINT with FLOCK PRINT and TUFT EMBROIDERY"
        techniques = self.extractor.extract_techniques(text)
        assert len(techniques) >= 2

    # ── Header Tests ──

    def test_extract_header_sp26(self):
        text = """DEPT:
STYLE NO  :SP26KB063
COLLECTION  :RAMADAN
BUYER: mOHIT
DESIGNER: malavika/SHAGUFTA
BOYS-KB
SEASON:SPRING 26"""
        header = self.extractor.extract_header(text)
        assert header.style_no == "SP26KB063"
        assert header.buyer == "Mohit"
        assert "Spring" in header.season or "SPRING" in header.season

    def test_extract_header_harley(self):
        text = """AUTUMN WINTER 2024-25
PRODUCT TYPE SEASON NAME FACTORY
STYLE DESCRIPTION COLORWAY DESIGNER
HD-SS-WT-07- REG 2024 IMPULSE
WOMEN'S S/S TEE BLACK/EXUBERANCE
LIFESTYLE WOMEN'S"""
        header = self.extractor.extract_header(text)
        assert "AUTUMN" in header.season.upper() or "WINTER" in header.season.upper()

    # ── Page Type Detection ──

    def test_is_bom_page(self):
        text = "BILL OF MATERIALS\nREF IMAGE\nBody- 95% Cotton/5% spandex"
        assert self.extractor.is_bom_page(text) is True

    def test_is_spec_page(self):
        text = "SPEC SHEET\nMeasurements in cm"
        assert self.extractor.is_spec_page(text) is True

    def test_is_artwork_page(self):
        text = "ARTWORK DETAIL\nTECHNIQUE:SCREEN PRINT"
        assert self.extractor.is_artwork_page(text) is True

    def test_not_artwork_page(self):
        text = "General garment specifications"
        assert self.extractor.is_artwork_page(text) is False

    # ── Vendor Tests ──

    def test_extract_vendors(self):
        text = "Avery Dennison sourced trims, vardhamann/coats thread"
        vendors = self.extractor.extract_vendors(text)
        assert len(vendors) >= 1

    # ── Full Metadata Tests ──

    def test_full_page_metadata(self):
        text = """SOLID 2 MM HD PRINT
TUFT EMBROIDERY
11-0601 TCX
BRIGHT WHITE
11 INCHES WIDTH
8 INCHES WIDTH
PRINT ARTWORK
FLOCK PRINT"""
        metadata = self.extractor.extract_page_metadata(text)
        assert len(metadata.techniques) >= 1
        assert len(metadata.pantone_colors) >= 1
        assert len(metadata.dimensions) >= 1


class TestArtworkEntry:
    """Test ArtworkEntry dataclass."""

    def test_to_sheet_row(self):
        from src.naming_engine import ArtworkEntry
        entry = ArtworkEntry(
            artwork_id="ART-001",
            style_no="SS25-001",
            buyer="Nike",
            season="Spring 2025",
            artwork_type="print",
            artwork_name="Screen Print - Left Chest",
            placement="Left Chest",
            color="17-1349 TCX (Exuberance)",
            size="8 x 6 cm",
            status="Pending",
            version="V1",
            techpack_page=2,
        )
        row = entry.to_sheet_row()
        assert len(row) == 20
        assert row[0] == "ART-001"
        assert row[1] == "SS25-001"
        assert row[2] == "Nike"
        assert row[16] == "Pending"
        assert row[17] == "V1"
