"""
Phase 2: Google Drive Integration
===================================
Handles:
- Service Account authentication
- Folder hierarchy creation on Google Drive
- File upload with duplicate detection
- Shareable link generation
- Mockups folder support
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
    DRIVE_FOLDERS,
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
        """Create a folder in Google Drive, returning its ID. Skips if already exists."""
        parent_id = parent_id or self.root_id
        existing = self._find(name, parent_id, folder=True)
        if existing:
            return existing
        meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
        f = self.service.files().create(body=meta, fields="id").execute()
        logger.info("Created folder: {} ({})", name, f["id"])
        return f["id"]

    def _find(self, name, parent_id, folder=False):
        """Find a file/folder by name within a parent folder."""
        mime = "and mimeType='application/vnd.google-apps.folder'" if folder else ""
        q = f"name='{name}' and '{parent_id}' in parents {mime} and trashed=false"
        r = self.service.files().list(q=q, fields="files(id)", pageSize=1).execute()
        files = r.get("files", [])
        return files[0]["id"] if files else None

    def create_structure(self, style_name: str) -> dict:
        """
        Create the full folder structure for a style on Google Drive.

        Structure:
          BRAND_STYLE/
          ├── Prints/
          ├── Embroidery/
          ├── Woven_Labels/
          ├── Heat_Transfers/
          ├── Patches_Badges/
          ├── Packaging/
          ├── Mockups/
          └── Unclassified/
        """
        style_id = self.create_folder(style_name)
        ids = {"root": style_id}

        for folder_name in DRIVE_FOLDERS:
            ids[folder_name] = self.create_folder(folder_name, style_id)

        # Also map category keys for backward compat
        for cat, info in ARTWORK_CATEGORIES.items():
            if info["folder_name"] in ids:
                ids[cat] = ids[info["folder_name"]]

        logger.info("Created Drive structure: {} ({} folders)", style_name, len(DRIVE_FOLDERS))
        return ids

    def upload_file(self, file_path: str, folder_id: str, custom_name=None) -> dict:
        """
        Upload a file to a Google Drive folder.
        Returns dict with file ID and shareable link.
        """
        fp = Path(file_path)
        name = custom_name or fp.name
        mimes = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".ai": "application/postscript",
            ".dst": "application/octet-stream",
        }
        mime = mimes.get(fp.suffix.lower(), "application/octet-stream")
        meta = {"name": name, "parents": [folder_id]}
        media = MediaFileUpload(str(fp), mimetype=mime, resumable=True)
        f = self.service.files().create(body=meta, media_body=media, fields="id,webViewLink").execute()

        file_id = f["id"]
        web_link = f.get("webViewLink", "")

        # Make the file shareable (anyone with link can view)
        try:
            self.service.permissions().create(
                fileId=file_id,
                body={"type": "anyone", "role": "reader"},
            ).execute()
        except Exception as e:
            logger.warning("Could not set sharing permissions: {}", e)

        logger.info("Uploaded {} → {} (link: {})", name, file_id, web_link)
        return {"id": file_id, "link": web_link, "name": name}

    def upload_results(self, output_dir: str, folder_ids: dict) -> dict:
        """
        Upload all processed files to Google Drive.
        Returns dict mapping local path → {id, link, name}.
        """
        output_dir = Path(output_dir)
        uploaded = {}

        for folder_name in DRIVE_FOLDERS:
            fid = folder_ids.get(folder_name)
            if not fid:
                continue

            local = output_dir / folder_name
            if not local.exists():
                continue

            for fp in local.rglob("*"):
                if fp.is_file():
                    result = self.upload_file(str(fp), fid)
                    uploaded[str(fp)] = result

        logger.info("Uploaded {} files to Drive", len(uploaded))
        return uploaded

    def get_shareable_link(self, file_id: str) -> str:
        """Get the shareable link for a file."""
        try:
            f = self.service.files().get(fileId=file_id, fields="webViewLink").execute()
            return f.get("webViewLink", "")
        except Exception as e:
            logger.warning("Could not get shareable link: {}", e)
            return ""

    def get_links_by_type(self, uploaded: dict) -> dict:
        """
        Organize uploaded file links by file type.
        Returns: {"png_links": [...], "pdf_links": [...], "ai_links": [...], "dst_links": [...]}
        """
        links = {"png_links": [], "pdf_links": [], "ai_links": [], "dst_links": []}

        for path, info in uploaded.items():
            ext = Path(path).suffix.lower()
            link = info.get("link", "")
            if not link:
                continue

            if ext == ".png":
                links["png_links"].append(link)
            elif ext == ".pdf":
                links["pdf_links"].append(link)
            elif ext == ".ai":
                links["ai_links"].append(link)
            elif ext == ".dst":
                links["dst_links"].append(link)

        return links
