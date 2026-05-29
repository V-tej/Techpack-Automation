"""
Phase 3: AI/OCR Detection Engine
==================================
Handles:
- Google Vision AI for image-based PDFs (OCR)
- OCR text extraction from scanned techpacks
- Google Gemini 2.5 Flash for multimodal artwork classification
  (replaces OpenAI GPT-4 Vision — supports native PDF + image input)
- Confidence scoring
"""

import base64
import io
import json
from pathlib import Path
from typing import Optional
from loguru import logger

from src.config import GEMINI_API_KEY, CONFIDENCE_THRESHOLD, ARTWORK_CATEGORIES


# ─────────────────────────────────────────────
# Gemini client (lazy singleton)
# ─────────────────────────────────────────────
_gemini_client = None


def _get_gemini_client():
    """Return a cached genai client, initialising once."""
    global _gemini_client
    if _gemini_client is None:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            _gemini_client = genai
            logger.info("Gemini client configured (API key loaded)")
        except ImportError:
            raise ImportError(
                "google-generativeai is not installed. "
                "Run: pip install google-generativeai"
            )
    return _gemini_client


# ─────────────────────────────────────────────
# OCR Engine — unchanged (Google Vision AI)
# ─────────────────────────────────────────────
class OCREngine:
    """Google Vision AI OCR for scanned/image-based techpack pages."""

    def __init__(self):
        from google.cloud import vision
        self.client = vision.ImageAnnotatorClient()
        logger.info("Google Vision OCR initialized")

    def extract_text(self, image_path: str) -> dict:
        from google.cloud import vision
        with open(image_path, "rb") as f:
            content = f.read()
        image = vision.Image(content=content)
        response = self.client.text_detection(image=image)
        texts = response.text_annotations
        if texts:
            return {"text": texts[0].description, "confidence": 0.9}
        return {"text": "", "confidence": 0.0}

    def extract_from_pdf_page(self, pdf_path: str, page_num: int) -> dict:
        import fitz
        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")
        doc.close()

        from google.cloud import vision
        image = vision.Image(content=img_bytes)
        response = self.client.text_detection(image=image)
        texts = response.text_annotations
        if texts:
            return {"text": texts[0].description, "confidence": 0.9, "page": page_num}
        return {"text": "", "confidence": 0.0, "page": page_num}


# ─────────────────────────────────────────────
# AI Classifier — Gemini 2.5 Flash
# ─────────────────────────────────────────────
class AIClassifier:
    """
    Gemini 1.5 Flash multimodal classifier for techpack artwork pages.

    Why Gemini 2.5 Flash:
    - Native PDF byte input (no manual image conversion needed)
    - 1M token context window → can process large multi-page PDFs
    - Vision + text understanding in one call
    - ~10x cheaper than GPT-4o, faster for batch processing
    - Already on Google Cloud (same ecosystem as Vision AI + Sheets)
    """

    # gemini-2.5-flash-lite: free-tier compatible, fast, multimodal vision
    # Switch to "gemini-2.5-flash" or "gemini-2.5-flash-lite" with a paid API key
    MODEL = "gemini-2.5-flash"

    def __init__(self):
        self.genai = _get_gemini_client()
        self.model = self.genai.GenerativeModel(self.MODEL)
        self.categories = list(ARTWORK_CATEGORIES.keys())
        logger.info("Gemini AIClassifier initialized (model={})", self.MODEL)

    def _build_prompt(self) -> str:
        """Build the classification prompt with project-specific categories."""
        cats = ", ".join(self.categories)
        return (
            "You are a garment production expert analysing a techpack document page.\n"
            "Classify the MAIN artwork / decoration shown on this page.\n\n"
            f"Valid categories: {cats}\n\n"
            "Rules:\n"
            "- Choose the single best-matching category from the list above.\n"
            "- 'print' covers screen print, DTF, sublimation, flock, puff, HD print etc.\n"
            "- 'embroidery' covers flat, 3D puff, tuft, chain stitch, applique etc.\n"
            "- 'woven_label' covers main label, size label, care/wash label, neck label.\n"
            "- 'heat_transfer' covers silicon/reflective/vinyl transfers, HT tape.\n"
            "- 'patch_badge' covers rubber/TPU/leather/woven/chenille/silicon patches & badges.\n"
            "- 'packaging' covers hangtag, hang tag, polybag, sticker, tissue, inserter.\n"
            "- If no artwork is detectable, return 'unclassified'.\n\n"
            "Respond ONLY with valid JSON, no markdown fences:\n"
            '{"category": "...", "confidence": 0.0-1.0, '
            '"technique": "...", "placement": "...", "colors": [...]}'
        )

    def classify_image(self, image_path: str) -> dict:
        """Classify a standalone image file (PNG / JPEG)."""
        ext = Path(image_path).suffix.lstrip(".").lower()
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")

        with open(image_path, "rb") as f:
            img_bytes = f.read()

        response = self.model.generate_content([
            self._build_prompt(),
            {"mime_type": mime, "data": img_bytes},
        ])

        return self._parse_response(response.text)

    def classify_pdf_page(self, pdf_path: str, page_num: int) -> dict:
        """
        Render a single PDF page to PNG and classify with Gemini vision.
        Uses PyMuPDF (fitz) at 2× scale for sharp artwork detail.
        """
        try:
            import fitz
        except ImportError:
            raise ImportError("PyMuPDF required: pip install PyMuPDF")

        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]
        # 2× scale gives ~1684×1188px for A4 — good balance of detail vs. API size
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")
        doc.close()

        logger.debug("Sending page {} ({} KB) to Gemini {}",
                     page_num, len(img_bytes) // 1024, self.MODEL)

        response = self.model.generate_content([
            self._build_prompt(),
            {"mime_type": "image/png", "data": img_bytes},
        ])

        result = self._parse_response(response.text)
        logger.info(
            "Gemini classified page {} → {} ({:.0%} confidence, technique={})",
            page_num, result.get("category"), result.get("confidence", 0),
            result.get("technique", ""),
        )
        return result

    def classify_full_pdf(self, pdf_path: str) -> list[dict]:
        """
        Send the raw PDF bytes directly to Gemini (native PDF support).
        Returns one result dict per page. Best for large or complex PDFs.
        """
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        prompt = (
            self._build_prompt()
            + "\n\nThis is a multi-page techpack PDF. "
            "Classify EACH page separately.\n"
            "Return a JSON array where each element corresponds to one page:\n"
            '[{"page": 1, "category": "...", "confidence": 0.0-1.0, '
            '"technique": "...", "placement": "...", "colors": [...]}, ...]'
        )

        response = self.model.generate_content([
            prompt,
            {"mime_type": "application/pdf", "data": pdf_bytes},
        ])

        try:
            raw = response.text.strip()
            # Strip accidental markdown fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            results = json.loads(raw)
            logger.info("Gemini full-PDF classification: {} page results", len(results))
            return results
        except (json.JSONDecodeError, IndexError):
            logger.warning("Gemini full-PDF response could not be parsed: {}", response.text[:200])
            return []

    # ── helpers ──────────────────────────────
    def _parse_response(self, text: str) -> dict:
        """Parse Gemini JSON response, stripping markdown fences if present."""
        try:
            raw = text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except (json.JSONDecodeError, IndexError):
            logger.warning("Gemini response could not be parsed: {}", text[:200])
            return {"category": "unclassified", "confidence": 0.0}


# ─────────────────────────────────────────────
# SmartDetector — unchanged interface
# ─────────────────────────────────────────────
class SmartDetector:
    """
    Combined detection: Keywords → OCR → Gemini AI (fallback chain).

    Level 1 — Keyword matching (fast, free, handles HD-SS-WT-07 style PDFs)
    Level 2 — Google Vision OCR (scanned/image-only pages like Design 4-Individualist)
    Level 3 — Gemini 1.5 Flash vision (pure vector/artwork pages like Design 1-Alpine)
    """

    def __init__(self, use_ocr: bool = True, use_ai: bool = True):
        self.ocr = OCREngine() if use_ocr else None
        self.ai = AIClassifier() if use_ai else None
        self.threshold = CONFIDENCE_THRESHOLD

    def detect(self, pdf_path: str, page_num: int, keyword_result: dict = None) -> dict:
        # Level 1: Keyword match (already done in pdf_processor)
        if keyword_result and keyword_result.get("confidence", 0) >= self.threshold:
            return {**keyword_result, "method": "keyword"}

        # Level 2: OCR
        if self.ocr:
            ocr_result = self.ocr.extract_from_pdf_page(pdf_path, page_num)
            if ocr_result["text"]:
                from src.pdf_processor import PDFProcessor
                processor = PDFProcessor()
                detections = processor.detect_artwork_type(ocr_result["text"])
                if detections and detections[0]["confidence"] >= self.threshold:
                    return {**detections[0], "method": "ocr"}

        # Level 3: Gemini AI Vision
        if self.ai:
            ai_result = self.ai.classify_pdf_page(pdf_path, page_num)
            if ai_result.get("confidence", 0) >= self.threshold:
                return {**ai_result, "method": "gemini"}

        return {"category": "unclassified", "confidence": 0.0, "method": "none"}
