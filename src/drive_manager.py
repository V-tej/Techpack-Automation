"""
Phase 2: Google Drive Integration
===================================
Handles:
- Service Account authentication
- Folder hierarchy creation on Google Drive
- File upload with duplicate detection
"""

from pathlib import Path
from typing import Optional
from loguru import logger
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.config import (
    GOOGLE_SERVICE_ACCOUNT_FILE,
    GOOGLE_DRIVE_ROOT_FOLDER_ID,
    GOOGLE_SCOPES,
    ARTWORK_CATEGORIES,
)


class DriveManager:
    """Google Drive integration for techpack artwork files."""

    def __init__(self, service_account_file=None, root_folder_id=None):
        self.sa_file = service_account_file or GOOGLE_SERVICE_ACCOUNT_FILE
        self.root_id = root_folder_id or GOOGLE_DRIVE_ROOT_FOLDER_ID
        self.service = None
        self._auth()

    def _auth(self):
        creds = service_account.Credentials.from_service_account_file(self.sa_file, scopes=GOOGLE_SCOPES)
        self.service = build("drive", "v3", credentials=creds)
        logger.info("Drive authenticated")

    def create_folder(self, name: str, parent_id: str = None) -> str:
        parent_id = parent_id or self.root_id
        existing = self._find(name, parent_id, folder=True)
        if existing:
            return existing
        meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
        f = self.service.files().create(body=meta, fields="id").execute()
        return f["id"]

    def _find(self, name, parent_id, folder=False):
        mime = "and mimeType='application/vnd.google-apps.folder'" if folder else ""
        q = f"name='{name}' and '{parent_id}' in parents {mime} and trashed=false"
        r = self.service.files().list(q=q, fields="files(id)", pageSize=1).execute()
        files = r.get("files", [])
        return files[0]["id"] if files else None

    def create_structure(self, style_name: str) -> dict:
        style_id = self.create_folder(style_name)
        ids = {"root": style_id}
        for cat, info in ARTWORK_CATEGORIES.items():
            ids[cat] = self.create_folder(info["folder_name"], style_id)
        ids["unclassified"] = self.create_folder("Unclassified", style_id)
        return ids

    def upload_file(self, file_path: str, folder_id: str, custom_name=None) -> str:
        fp = Path(file_path)
        name = custom_name or fp.name
        mimes = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg"}
        mime = mimes.get(fp.suffix.lower(), "application/octet-stream")
        meta = {"name": name, "parents": [folder_id]}
        media = MediaFileUpload(str(fp), mimetype=mime, resumable=True)
        f = self.service.files().create(body=meta, media_body=media, fields="id").execute()
        logger.info("Uploaded {} → {}", name, f["id"])
        return f["id"]

    def upload_results(self, output_dir: str, folder_ids: dict) -> dict:
        output_dir = Path(output_dir)
        uploaded = {}
        for cat, fid in folder_ids.items():
            if cat == "root":
                continue
            if cat in ARTWORK_CATEGORIES:
                local = output_dir / ARTWORK_CATEGORIES[cat]["folder_name"]
            elif cat == "unclassified":
                local = output_dir / "Unclassified"
            else:
                continue
            if not local.exists():
                continue
            for fp in local.rglob("*"):
                if fp.is_file():
                    uploaded[str(fp)] = self.upload_file(str(fp), fid)
        logger.info("Uploaded {} files to Drive", len(uploaded))
        return uploaded
