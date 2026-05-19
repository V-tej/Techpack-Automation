"""
Tests for PDF Processor (Phase 1) — Updated for real techpack text
"""
import pytest
from pathlib import Path
from src.pdf_processor import PDFProcessor, ArtworkDetection


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

    def test_no_detection(self):
        text = "General specifications and measurements"
        results = self.processor.detect_artwork_type(text)
        assert len(results) == 0

    def test_multiple_detections(self):
        text = "Screen print artwork with embroidery detail and woven label"
        results = self.processor.detect_artwork_type(text)
        assert len(results) >= 2

    def test_confidence_scoring(self):
        text = "screen print dtf sublimation digital print pigment print"
        results = self.processor.detect_artwork_type(text)
        assert results[0]["confidence"] > 0.5

    # ── Tests with real techpack text ──

    def test_no_false_positive_ht_in_bright(self):
        """'ht' should NOT match inside 'BRIGHT' or 'HEIGHT'."""
        text = "BRIGHT WHITE 11-0601 TCX HEIGHT 5CM"
        results = self.processor.detect_artwork_type(text)
        ht_results = [r for r in results if r["category"] == "heat_transfer"]
        assert len(ht_results) == 0

    def test_real_heat_transfer(self):
        """Real heat transfer text from HD-SS-WT-07 page 4."""
        text = "HEAT TRANSFER AT INNER YOKE silicon label 3mm raised HT proportional"
        results = self.processor.detect_artwork_type(text)
        assert results[0]["category"] == "heat_transfer"
        assert results[0]["confidence"] > 0.3

    def test_real_embroidery(self):
        """Real embroidery text from SP26KB063 page 2."""
        text = "EMBROIDERY IN COTTON POLY THREAD puffed embroidery"
        results = self.processor.detect_artwork_type(text)
        assert results[0]["category"] == "embroidery"

    def test_real_bom_page(self):
        """Bill of Materials page should be detected."""
        text = "BILL OF MATERIALS REF IMAGE Body 95% Cotton DESCRIPTION CONTENT/FINISH PLACEMENT CONSUMPTION SOURCE"
        results = self.processor.detect_artwork_type(text)
        assert results[0]["category"] == "bill_of_materials"

    def test_real_design_sheet(self):
        """Design sheet page from SP26KB063 page 1."""
        text = "DESIGN SHEET STYLE DESCRIPTION FASHION PRINTED POLO"
        results = self.processor.detect_artwork_type(text)
        assert results[0]["category"] == "design_sheet"

    def test_real_washcare_label(self):
        """Washcare label page from SP26KB063 page 7."""
        text = "WASHCARE LABEL MATERIAL SATIN USE SAME FONT ADD COUNTRY OF ORIGIN"
        results = self.processor.detect_artwork_type(text)
        assert results[0]["category"] == "woven_label"

    def test_real_spec_sheet(self):
        """Spec/reference sheet page."""
        text = "REFERENCE SHEET some garment dimensions and details"
        results = self.processor.detect_artwork_type(text)
        assert results[0]["category"] == "spec_sheet"

    def test_real_branding_badge(self):
        """Silicon branding badge from HD-SS-WT-07 page 7."""
        text = "BRANDING BADGE poly/elastane with stretch silicon branding SILICON BADGE at outer CB"
        results = self.processor.detect_artwork_type(text)
        assert results[0]["category"] == "patch_badge"

    def test_real_packaging(self):
        """Packaging page with tissue paper, carton box etc."""
        text = "Tissue paper BOPP Self seal poly cover carton box inserter crocodile clip"
        results = self.processor.detect_artwork_type(text)
        assert results[0]["category"] == "packaging"

    def test_no_false_print_on_spec_page(self):
        """Spec pages with generic text should NOT be classified as 'print'."""
        text = "DEPT: BOYS STYLE NO: SP26KB063 COLLECTION: RAMADAN BUYER: MOHIT SPRING 26"
        results = self.processor.detect_artwork_type(text)
        print_results = [r for r in results if r["category"] == "print"]
        assert len(print_results) == 0


class TestNamingEngine:
    """Test naming convention generation."""

    def test_generate_id(self):
        from src.naming_engine import NamingEngine
        namer = NamingEngine()
        id1 = namer.generate_id("print")
        id2 = namer.generate_id("print")
        assert id1 == "ART-001"
        assert id2 == "ART-002"

    def test_generate_filename(self):
        from src.naming_engine import NamingEngine
        namer = NamingEngine()
        name = namer.generate_filename("NIKE", "SS25-001", "print")
        assert "NIKE" in name
        assert "SS25-001" in name
        assert "PRINTS" in name
