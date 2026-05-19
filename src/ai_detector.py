"""
Phase 3: AI/OCR Detection Engine
==================================
Handles:
- Google Vision AI for image-based PDFs
- OCR text extraction from scanned techpacks
- OpenAI GPT-4 Vision for artwork classification
- Confidence scoring
"""

import base64
import io
from pathlib import Path
from typing import Optional
from loguru import logger

from src.config import OPENAI_API_KEY, CONFIDENCE_THRESHOLD, ARTWORK_CATEGORIES


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


class AIClassifier:
    """OpenAI GPT-4 Vision for intelligent artwork classification."""

    def __init__(self, api_key: str = None):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key or OPENAI_API_KEY)
        self.categories = list(ARTWORK_CATEGORIES.keys())
        logger.info("AI Classifier initialized")

    def classify_image(self, image_path: str) -> dict:
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        ext = Path(image_path).suffix.lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")

        prompt = (
            "You are a garment production expert. Classify this techpack artwork image.\n"
            f"Categories: {', '.join(self.categories)}\n"
            "Return JSON: {\"category\": \"...\", \"confidence\": 0.0-1.0, "
            "\"technique\": \"...\", \"placement\": \"...\", \"colors\": [...]}"
        )

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
                ]
            }],
            max_tokens=300,
        )

        import json
        try:
            result = json.loads(response.choices[0].message.content)
            logger.info("AI classified: {} ({:.0%})", result["category"], result["confidence"])
            return result
        except (json.JSONDecodeError, KeyError):
            logger.warning("AI classification failed to parse")
            return {"category": "unclassified", "confidence": 0.0}

    def classify_pdf_page(self, pdf_path: str, page_num: int) -> dict:
        import fitz
        doc = fitz.open(pdf_path)
        page = doc[page_num - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_bytes = pix.tobytes("png")
        doc.close()

        b64 = base64.b64encode(img_bytes).decode("utf-8")

        prompt = (
            "Classify this garment techpack page artwork.\n"
            f"Categories: {', '.join(self.categories)}\n"
            "Return JSON: {\"category\": \"...\", \"confidence\": 0.0-1.0, "
            "\"technique\": \"...\", \"placement\": \"...\", \"colors\": [...]}"
        )

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                ]
            }],
            max_tokens=300,
        )

        import json
        try:
            return json.loads(response.choices[0].message.content)
        except (json.JSONDecodeError, KeyError):
            return {"category": "unclassified", "confidence": 0.0}


class SmartDetector:
    """Combined detection: Keywords → OCR → AI (fallback chain)."""

    def __init__(self, use_ocr=True, use_ai=True):
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

        # Level 3: AI Vision
        if self.ai:
            ai_result = self.ai.classify_pdf_page(pdf_path, page_num)
            if ai_result.get("confidence", 0) >= self.threshold:
                return {**ai_result, "method": "ai"}

        return {"category": "unclassified", "confidence": 0.0, "method": "none"}
