"""
Phase 6: Web Dashboard — Techpack Artwork Automation
======================================================
Flask backend serving the dashboard UI.
Run: python dashboard.py
Then open: http://localhost:5000
"""

import os
import sys
import json
import shutil
import threading
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import OUTPUT_DIR, ARTWORK_CATEGORIES
from src.pdf_processor import PDFProcessor
from src.naming_engine import NamingEngine, ArtworkEntry, ReportGenerator

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB max upload

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory job store (simple, no DB needed)
jobs = {}


def run_pipeline(job_id: str, pdf_path: str, brand: str, style: str):
    """Run the full processing pipeline in a background thread."""
    job = jobs[job_id]
    job["status"] = "processing"
    job["logs"] = []

    def log(msg):
        job["logs"].append({"time": datetime.now().strftime("%H:%M:%S"), "msg": msg})

    try:
        log("Starting PDF processing...")
        processor = PDFProcessor()

        log("Extracting text from all pages...")
        result = processor.process_techpack(pdf_path, str(OUTPUT_DIR / Path(pdf_path).stem))

        log(f"Detected {len(result.detections)} artworks across {result.total_pages} pages")

        log("Splitting PDF into category folders...")
        output_files = processor.split_pdf(pdf_path, result)

        log("Applying naming conventions...")
        namer = NamingEngine()
        namer.rename_files(result.output_dir, brand, style)

        entries = []
        for det in result.detections:
            art_id = namer.generate_id(det.category)
            entries.append(ArtworkEntry(
                artwork_id=art_id,
                category=det.category,
                confidence=det.confidence,
                detection_method="keyword",
                file_name=f"{brand}_{style}_{det.category}",
                date_added=datetime.now().strftime("%Y-%m-%d %H:%M"),
            ))

        log("Generating summary report...")
        report_path = Path(result.output_dir) / "ARTWORK_SUMMARY.md"
        ReportGenerator().generate_summary(entries, str(report_path))

        # Build category summary
        category_counts = {}
        for det in result.detections:
            cat = det.category
            category_counts[cat] = category_counts.get(cat, 0) + 1

        job["status"] = "done"
        job["result"] = {
            "total_pages": result.total_pages,
            "classified": len(result.detections),
            "unclassified": len(result.unclassified_pages),
            "unclassified_pages": result.unclassified_pages,
            "output_dir": result.output_dir,
            "categories": category_counts,
            "entries": [
                {
                    "id": e.artwork_id,
                    "category": e.category,
                    "confidence": e.confidence,
                    "file": e.file_name,
                    "date": e.date_added,
                }
                for e in entries
            ],
        }
        log(f"Complete! {len(entries)} artworks organized into {len(category_counts)} categories.")

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        log(f"Error: {e}")


@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    f = request.files["file"]
    brand = request.form.get("brand", "BRAND").upper().strip()
    style = request.form.get("style", "STYLE").upper().strip()

    if not f.filename.endswith(".pdf"):
        return jsonify({"error": "Only PDF files are supported"}), 400

    # Save uploaded file
    safe_name = f.filename.replace(" ", "_")
    upload_path = UPLOAD_DIR / safe_name
    f.save(str(upload_path))

    # Create job
    job_id = f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    jobs[job_id] = {
        "id": job_id,
        "filename": f.filename,
        "brand": brand,
        "style": style,
        "status": "queued",
        "logs": [],
        "result": None,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Run in background thread
    thread = threading.Thread(
        target=run_pipeline,
        args=(job_id, str(upload_path), brand, style),
        daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/job/<job_id>")
def get_job(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(jobs[job_id])


@app.route("/api/jobs")
def list_jobs():
    return jsonify(list(reversed(list(jobs.values()))))


@app.route("/api/categories")
def categories():
    return jsonify({
        k: {"folder": v["folder_name"], "prefix": v["code_prefix"]}
        for k, v in ARTWORK_CATEGORIES.items()
    })


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  Techpack Artwork Automation Dashboard")
    print("  Open your browser: http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(debug=True, port=5000, use_reloader=False)
