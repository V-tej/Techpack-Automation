"""
Phase 6: Web Dashboard — Techpack Artwork Automation
======================================================
Flask backend serving the dashboard UI.
Includes:
- PDF upload and processing
- Live status and logs
- Webhook endpoints for Make/Zapier
- Artwork approval workflow API
- Vendor management API
- Category color coding

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

from src.config import OUTPUT_DIR, ARTWORK_CATEGORIES, CATEGORY_COLORS
from src.pdf_processor import PDFProcessor
from src.naming_engine import (
    NamingEngine, ArtworkEntry, ReportGenerator,
    VendorEntry, UploadLogEntry, ApprovalEntry,
)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max upload

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

        log("Extracting text and metadata from all pages...")
        result = processor.process_techpack(pdf_path, str(OUTPUT_DIR / Path(pdf_path).stem))

        # Extract header info
        header = result.header_info
        if header:
            log(f"Detected — Style: {header.style_no}, Buyer: {header.buyer}, Season: {header.season}")
            if header.style_no and style == "STYLE":
                style_used = header.style_no
            else:
                style_used = style
        else:
            style_used = style

        log(f"Detected {len(result.detections)} artworks across {result.total_pages} pages")

        if result.all_vendors:
            log(f"Vendors found: {', '.join(result.all_vendors)}")

        log("Splitting PDF into category folders...")
        output_files = processor.split_pdf(pdf_path, result)

        log("Extracting artwork images...")
        extracted_images = processor.extract_images(pdf_path, result)
        log(f"Extracted {len(extracted_images)} artwork images")

        log("Applying naming conventions...")
        namer = NamingEngine()
        namer.rename_files(result.output_dir, brand, style_used)

        entries = []
        for det in result.detections:
            art_id = namer.generate_id(det.category)

            colors_str = ", ".join(
                f"{c['code']} ({c['name']})" if isinstance(c, dict) else str(c)
                for c in det.pantone_colors
            ) if det.pantone_colors else ""

            entry = ArtworkEntry(
                artwork_id=art_id,
                style_no=style_used,
                buyer=header.buyer if header else "",
                season=header.season if header else "",
                garment_type=header.garment_type if header else "",
                artwork_type=det.category,
                artwork_name=det.artwork_name or "",
                placement=", ".join(det.placements) if det.placements else "",
                color=colors_str,
                size=", ".join(det.dimensions) if det.dimensions else "",
                file_name=namer.generate_filename(brand, style_used, det.category),
                vendor=", ".join(det.vendors) if det.vendors else "",
                status="Pending",
                version="V1",
                techpack_page=det.page_number,
                notes=", ".join(det.techniques) if det.techniques else "",
                confidence=det.confidence,
                detection_method="keyword",
                date_added=datetime.now().strftime("%Y-%m-%d %H:%M"),
            )
            entries.append(entry)

        log("Generating summary report...")
        report_path = Path(result.output_dir) / "ARTWORK_SUMMARY.md"
        ReportGenerator().generate_summary(entries, str(report_path), header_info=header)

        # Build category summary with colors
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
            "images_extracted": len(extracted_images),
            "vendors": result.all_vendors,
            "header": {
                "style_no": header.style_no if header else "",
                "buyer": header.buyer if header else "",
                "season": header.season if header else "",
                "garment_type": header.garment_type if header else "",
                "designer": header.designer if header else "",
            } if header else {},
            "categories": {
                cat: {
                    "count": count,
                    "color_hex": CATEGORY_COLORS.get(cat, {}).get("hex", "#6B7280"),
                    "color_name": CATEGORY_COLORS.get(cat, {}).get("name", "Gray"),
                }
                for cat, count in category_counts.items()
            },
            "entries": [
                {
                    "id": e.artwork_id,
                    "category": e.artwork_type,
                    "artwork_name": e.artwork_name,
                    "placement": e.placement,
                    "color": e.color,
                    "size": e.size,
                    "technique": e.notes,
                    "vendor": e.vendor,
                    "status": e.status,
                    "version": e.version,
                    "page": e.techpack_page,
                    "confidence": e.confidence,
                    "file": e.file_name,
                    "date": e.date_added,
                    "color_hex": CATEGORY_COLORS.get(e.artwork_type, {}).get("hex", "#6B7280"),
                }
                for e in entries
            ],
        }
        log(f"Complete! {len(entries)} artworks organized into {len(category_counts)} categories.")

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        log(f"Error: {e}")


# ── Page Routes ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")


# ── Upload & Processing ─────────────────────────────────────

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


# ── Job Status ──────────────────────────────────────────────

@app.route("/api/job/<job_id>")
def get_job(job_id):
    if job_id not in jobs:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(jobs[job_id])


@app.route("/api/jobs")
def list_jobs():
    return jsonify(list(reversed(list(jobs.values()))))


# ── Categories ──────────────────────────────────────────────

@app.route("/api/categories")
def categories():
    return jsonify({
        k: {
            "folder": v["folder_name"],
            "prefix": v["code_prefix"],
            "color_hex": v["color_hex"],
            "color_name": v["color_name"],
        }
        for k, v in ARTWORK_CATEGORIES.items()
    })


# ── Webhook for Make/Zapier ─────────────────────────────────

@app.route("/api/webhook/process", methods=["POST"])
def webhook_process():
    """
    Webhook endpoint for Make/Zapier integration.
    Accepts JSON payload:
    {
        "pdf_url": "https://...",      (optional — URL to download PDF)
        "pdf_path": "/path/to/file",   (optional — local path)
        "brand": "NIKE",
        "style": "SS25-001"
    }
    Returns job_id for status polling.
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON payload required"}), 400

    brand = data.get("brand", "BRAND").upper().strip()
    style = data.get("style", "STYLE").upper().strip()
    pdf_path = data.get("pdf_path", "")

    if not pdf_path:
        return jsonify({"error": "pdf_path is required"}), 400

    if not Path(pdf_path).exists():
        return jsonify({"error": f"PDF not found: {pdf_path}"}), 404

    # Create job
    job_id = f"webhook_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    jobs[job_id] = {
        "id": job_id,
        "filename": Path(pdf_path).name,
        "brand": brand,
        "style": style,
        "status": "queued",
        "logs": [],
        "result": None,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "webhook",
    }

    thread = threading.Thread(
        target=run_pipeline,
        args=(job_id, pdf_path, brand, style),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id, "status": "queued"})


# ── Approval Workflow API ───────────────────────────────────

@app.route("/api/artworks/<artwork_id>/approve", methods=["POST"])
def approve_artwork(artwork_id):
    """
    Update artwork approval status.
    JSON payload: {"status": "Approved"} or {"status": "Rejected"}
    """
    data = request.get_json()
    if not data or "status" not in data:
        return jsonify({"error": "status is required"}), 400

    new_status = data["status"]
    valid_statuses = ["Pending", "Approved", "Rejected", "Revision"]
    if new_status not in valid_statuses:
        return jsonify({"error": f"Invalid status. Must be one of: {valid_statuses}"}), 400

    # Update in latest job results
    for job in reversed(list(jobs.values())):
        if job.get("result") and job["result"].get("entries"):
            for entry in job["result"]["entries"]:
                if entry["id"] == artwork_id:
                    entry["status"] = new_status
                    return jsonify({"id": artwork_id, "status": new_status})

    return jsonify({"error": "Artwork not found"}), 404


@app.route("/api/artworks/<artwork_id>/version", methods=["POST"])
def update_version(artwork_id):
    """
    Update artwork version.
    JSON payload: {"version": "V2"} or {"version": "FINAL"}
    """
    data = request.get_json()
    if not data or "version" not in data:
        return jsonify({"error": "version is required"}), 400

    new_version = data["version"]
    valid_versions = ["V1", "V2", "V3", "FINAL", "APPROVED"]
    if new_version not in valid_versions:
        return jsonify({"error": f"Invalid version. Must be one of: {valid_versions}"}), 400

    for job in reversed(list(jobs.values())):
        if job.get("result") and job["result"].get("entries"):
            for entry in job["result"]["entries"]:
                if entry["id"] == artwork_id:
                    entry["version"] = new_version
                    return jsonify({"id": artwork_id, "version": new_version})

    return jsonify({"error": "Artwork not found"}), 404


# ── Vendor API ──────────────────────────────────────────────

@app.route("/api/vendors")
def get_vendors():
    """Get all unique vendors from processed jobs."""
    all_vendors = set()
    for job in jobs.values():
        if job.get("result") and job["result"].get("vendors"):
            all_vendors.update(job["result"]["vendors"])
    return jsonify(sorted(list(all_vendors)))


# ── Artworks List API ───────────────────────────────────────

@app.route("/api/artworks")
def get_artworks():
    """Get all artworks from the latest completed job."""
    for job in reversed(list(jobs.values())):
        if job.get("result") and job["result"].get("entries"):
            return jsonify(job["result"]["entries"])
    return jsonify([])


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  Techpack Artwork Automation Dashboard")
    print("  Open your browser: http://localhost:5000")
    print("=" * 50 + "\n")
    app.run(host="0.0.0.0", debug=True, port=5000, use_reloader=False)
