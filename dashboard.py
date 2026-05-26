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
import queue
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
from src.credentials_helper import init_credentials

# Initialize dynamic Base64 credentials for Google Drive & Sheets APIs on startup
init_credentials()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB max upload

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory job store (simple, no DB needed)
jobs = {}

# Thread-safe sequential processing queue & locks
job_queue = queue.Queue()
active_job_id = None
active_job_lock = threading.Lock()


def run_pipeline(job_id: str, pdf_path: str, brand: str, style: str):
    """Run the full processing pipeline in a background thread."""
    job = jobs[job_id]
    job["status"] = "processing"
    job["logs"] = []

    def log(msg):
        from loguru import logger
        job["logs"].append({"time": datetime.now().strftime("%H:%M:%S"), "msg": msg})
        logger.info(f"[{job_id}] {msg}")

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

        # ── Phase 4: Google Drive Upload ──
        try:
            log("Uploading files to Google Drive...")
            from src.drive_manager import DriveManager
            drive = DriveManager()
            folder_ids = drive.create_structure(f"{brand}_{style_used}")
            uploaded = drive.upload_results(str(result.output_dir), folder_ids)

            # Update entries with Drive links
            for entry in entries:
                for path, info in uploaded.items():
                    if entry.artwork_type in path.lower() or \
                       ARTWORK_CATEGORIES.get(entry.artwork_type, {}).get("folder_name", "") in path:
                        ext = Path(path).suffix.lower()
                        link = info.get("link", "")
                        if ext == ".png":
                            entry.png_link = link
                        elif ext == ".pdf":
                            entry.pdf_link = link
            log("Google Drive upload completed successfully.")
        except Exception as drive_err:
            log(f"Warning: Google Drive upload skipped/failed: {drive_err}")

        # ── Phase 5: Update Google Sheets ──
        try:
            log("Updating Google Sheets database...")
            from src.naming_engine import SheetsDatabase
            db = SheetsDatabase()

            # Add artwork entries
            db.add_artworks_batch(entries)

            # Add vendors discovered from BOM pages
            if result.all_vendors:
                vendor_entries = []
                for v in result.all_vendors:
                    vendor_entries.append(VendorEntry(vendor_name=v))
                db.add_vendors_batch(vendor_entries)

            # Log the upload
            db.log_upload(UploadLogEntry(
                style_no=style_used,
                uploaded_by="Dashboard",
                status="Success",
            ))

            # Create approval records
            approval_entries = []
            for entry in entries:
                approval_entries.append(ApprovalEntry(
                    style=style_used,
                    artwork=entry.artwork_id,
                    buyer_approval="Pending",
                    vendor_approval="Pending",
                ))
            db.add_approvals_batch(approval_entries)
            log("Google Sheets database updated successfully.")
        except Exception as sheet_err:
            log(f"Warning: Google Sheets update failed: {sheet_err}")

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
            "drive_link": f"https://drive.google.com/drive/folders/{folder_ids['root']}" if ('folder_ids' in locals() and folder_ids and folder_ids.get('root')) else "",
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
                    "png_link": getattr(e, "png_link", ""),
                    "pdf_link": getattr(e, "pdf_link", ""),
                }
                for e in entries
            ],
        }
        log(f"Complete! {len(entries)} artworks organized into {len(category_counts)} categories.")

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        log(f"Error: {e}")


def worker():
    """Persistent background worker thread that processes jobs sequentially."""
    global active_job_id
    from loguru import logger
    logger.info("Sequential Queue Worker Thread started successfully.")
    
    while True:
        try:
            # Blocks until a job is available
            job_data = job_queue.get()
            if job_data is None:
                # Poison pill to stop the thread
                break
                
            job_id, pdf_path, brand, style = job_data
            
            with active_job_lock:
                active_job_id = job_id
                
            logger.info(f"Worker picked up job {job_id}. Starting processing...")
            
            # Run the actual pipeline
            run_pipeline(job_id, pdf_path, brand, style)
            
        except Exception as e:
            logger.error(f"Error in sequential worker thread: {e}")
        finally:
            with active_job_lock:
                active_job_id = None
            job_queue.task_done()


# Start the sequential background worker thread
worker_thread = threading.Thread(target=worker, daemon=True)
worker_thread.start()


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

    # Append initial queue status log
    jobs[job_id]["logs"].append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "msg": "Added to sequential processing queue. Waiting for prior uploads to finish..."
    })

    # Add to sequential processing queue
    job_queue.put((job_id, str(upload_path), brand, style))

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

    # Append initial queue status log
    jobs[job_id]["logs"].append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "msg": "Webhook job added to sequential processing queue. Waiting for prior uploads to finish..."
    })

    # Add to sequential processing queue
    job_queue.put((job_id, pdf_path, brand, style))

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
    print("  Open your browser: http://localhost:5001")
    print("=" * 50 + "\n")
    app.run(host="0.0.0.0", debug=True, port=5001, use_reloader=False)
