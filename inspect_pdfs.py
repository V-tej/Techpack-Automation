"""Inspect what text is extracted from both sample PDFs."""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.pdf_processor import PDFProcessor

processor = PDFProcessor()

for pdf in [
    "samples/HD-SS-WT-07 WOMENS TEE-21-05-24.pdf",
    "samples/SP26KB063.pdf",
]:
    print("=" * 80)
    print(f"FILE: {pdf}")
    print("=" * 80)
    pages = processor.extract_text(pdf)
    for p in pages:
        print(f"\n--- PAGE {p['page_number']} ({len(p['text'])} chars, images={p['has_images']}) ---")
        print(p["text"][:800])
        
        # Show what the detector finds
        detections = processor.detect_artwork_type(p["text"])
        if detections:
            for d in detections:
                print(f"  >> DETECTED: {d['category']} (confidence={d['confidence']:.0%}, keywords={d['keywords_found']})")
        else:
            print("  >> NO DETECTION")
        print()
