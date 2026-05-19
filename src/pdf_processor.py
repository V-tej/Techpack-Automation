"""
Phase 1: PDF Processing Engine
================================
Handles:
- PDF parsing and text extraction (pypdf - pure Python)
- Keyword-based artwork type detection
- Automatic page splitting by artwork category
- Local folder structure creation

Note: Uses pypdf as primary engine (no DLL dependencies).
PyMuPDF (fitz) used as fallback if available.
"""

from pathlib import Path
from loguru import logger
from dataclasses import dataclass, field

from src.config import ARTWORK_CATEGORIES, OUTPUT_DIR


@dataclass
class ArtworkDetection:
    """Represents a detected artwork on a specific page."""
    page_number: int
    category: str
    code_prefix: str
    keywords_found: list = field(default_factory=list)
    confidence: float = 0.0
    text_content: str = ""
    has_images: bool = False


@dataclass
class TechpackResult:
    """Result of processing a single techpack PDF."""
    source_file: str
    total_pages: int
    detections: list = field(default_factory=list)
    unclassified_pages: list = field(default_factory=list)
    output_dir: str = ""


class PDFProcessor:
    """
    Core PDF processing engine.
    Uses pypdf for text extraction (pure Python, no DLL needed).
    """

    def __init__(self, keyword_config: dict = None):
        self.categories = keyword_config or ARTWORK_CATEGORIES
        logger.info("PDFProcessor initialized with {} artwork categories", len(self.categories))

    def extract_text(self, pdf_path: str) -> list:
        """Extract text from every page of a PDF using pypdf."""
        from pypdf import PdfReader

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        pages_data = []
        reader = PdfReader(str(pdf_path))

        for page_num, page in enumerate(reader.pages):
            text = page.extract_text() or ""

            pages_data.append({
                "page_number": page_num + 1,
                "text": text.strip(),
                "image_count": len(page.images) if hasattr(page, "images") else 0,
                "has_images": len(page.images) > 0 if hasattr(page, "images") else False,
            })

            logger.debug("Page {}: {} chars text", page_num + 1, len(text))

        logger.info("Extracted {} pages from {}", len(pages_data), pdf_path.name)
        return pages_data

    def detect_artwork_type(self, text: str) -> list:
        """Detect artwork type(s) from text using keyword matching."""
        text_lower = text.lower()
        detections = []

        for category_name, category_info in self.categories.items():
            keywords_found = []
            for keyword in category_info["keywords"]:
                if keyword.lower() in text_lower:
                    keywords_found.append(keyword)

            if keywords_found:
                confidence = len(keywords_found) / len(category_info["keywords"])
                confidence = min(confidence * 1.5, 1.0)
                detections.append({
                    "category": category_name,
                    "code_prefix": category_info["code_prefix"],
                    "folder_name": category_info["folder_name"],
                    "keywords_found": keywords_found,
                    "confidence": round(confidence, 2),
                })

        detections.sort(key=lambda x: x["confidence"], reverse=True)
        return detections

    def process_techpack(self, pdf_path: str, output_dir: str = None) -> TechpackResult:
        """Process a complete techpack PDF end-to-end."""
        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir) if output_dir else OUTPUT_DIR / pdf_path.stem

        logger.info("Processing techpack: {}", pdf_path.name)
        pages_data = self.extract_text(str(pdf_path))

        result = TechpackResult(
            source_file=str(pdf_path),
            total_pages=len(pages_data),
            output_dir=str(output_dir),
        )

        for page_data in pages_data:
            page_num = page_data["page_number"]
            text = page_data["text"]

            if not text and not page_data["has_images"]:
                logger.warning("Page {} is blank", page_num)
                result.unclassified_pages.append(page_num)
                continue

            detections = self.detect_artwork_type(text)

            if detections:
                best = detections[0]
                detection = ArtworkDetection(
                    page_number=page_num,
                    category=best["category"],
                    code_prefix=best["code_prefix"],
                    keywords_found=best["keywords_found"],
                    confidence=best["confidence"],
                    text_content=text[:500],
                    has_images=page_data["has_images"],
                )
                result.detections.append(detection)
                logger.info(
                    "Page {} -> {} (confidence: {:.0%}, keywords: {})",
                    page_num, best["category"], best["confidence"],
                    ", ".join(best["keywords_found"])
                )
            else:
                result.unclassified_pages.append(page_num)
                logger.warning("Page {} - no keyword match, unclassified", page_num)

        logger.info(
            "Done: {} pages, {} classified, {} unclassified",
            result.total_pages, len(result.detections), len(result.unclassified_pages)
        )
        return result

    def split_pdf(self, pdf_path: str, result: TechpackResult) -> dict:
        """Split the PDF into separate files based on artwork categories."""
        from pypdf import PdfReader, PdfWriter

        pdf_path = Path(pdf_path)
        output_dir = Path(result.output_dir)
        output_files = {}

        reader = PdfReader(str(pdf_path))

        # Group pages by category
        category_pages = {}
        for detection in result.detections:
            cat = detection.category
            if cat not in category_pages:
                category_pages[cat] = []
            category_pages[cat].append(detection.page_number)

        # Write one PDF per category
        for category, pages in category_pages.items():
            folder_name = self.categories[category]["folder_name"]
            category_dir = output_dir / folder_name
            category_dir.mkdir(parents=True, exist_ok=True)

            writer = PdfWriter()
            for page_num in sorted(pages):
                writer.add_page(reader.pages[page_num - 1])

            output_path = category_dir / f"{pdf_path.stem}_{folder_name}.pdf"
            with open(output_path, "wb") as f:
                writer.write(f)

            output_files[category] = str(output_path)
            logger.info("Created {} - {} pages -> {}", folder_name, len(pages), output_path.name)

        # Unclassified pages
        if result.unclassified_pages:
            unclassified_dir = output_dir / "Unclassified"
            unclassified_dir.mkdir(parents=True, exist_ok=True)

            writer = PdfWriter()
            for page_num in result.unclassified_pages:
                writer.add_page(reader.pages[page_num - 1])

            output_path = unclassified_dir / f"{pdf_path.stem}_Unclassified.pdf"
            with open(output_path, "wb") as f:
                writer.write(f)

            output_files["unclassified"] = str(output_path)
            logger.warning("Unclassified pages: {} -> {}", result.unclassified_pages, output_path.name)

        return output_files
