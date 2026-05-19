"""
Tests for PDF Processor (Phase 1)
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
        text = "Print artwork with embroidery detail and woven label"
        results = self.processor.detect_artwork_type(text)
        assert len(results) >= 2

    def test_confidence_scoring(self):
        text = "screen print dtf sublimation digital print pigment print"
        results = self.processor.detect_artwork_type(text)
        assert results[0]["confidence"] > 0.5


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
