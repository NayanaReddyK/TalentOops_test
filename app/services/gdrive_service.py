"""Google Drive resume fetcher & parser service (Strict Real Production Mode)."""
from __future__ import annotations

import logging
import os
import re
import urllib.request
import uuid
from typing import Any

from pypdf import PdfReader

logger = logging.getLogger("talentops.gdrive")

_EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


def extract_email_from_text(text: str) -> str:
    """Extract candidate email address from resume text."""
    matches = _EMAIL_REGEX.findall(text)
    if matches:
        for m in matches:
            if not any(ignore in m.lower() for ignore in ["example.com", "domain.com", "github.com"]):
                return m
        return matches[0]
    return ""


def extract_drive_id_and_kind(drive_url_or_id: str) -> tuple[str, str]:
    """Extract Google Drive ID and kind ('file' or 'folder') from a URL or raw ID string."""
    if not drive_url_or_id:
        return "", "folder"
    if "drive.google.com" in drive_url_or_id:
        match_folder = re.search(r"folders/([a-zA-Z0-9_-]+)", drive_url_or_id)
        if match_folder:
            return match_folder.group(1), "folder"
        match_file = re.search(r"file/d/([a-zA-Z0-9_-]+)", drive_url_or_id)
        if match_file:
            return match_file.group(1), "file"
        match_id = re.search(r"id=([a-zA-Z0-9_-]+)", drive_url_or_id)
        if match_id:
            return match_id.group(1), "file"
    return drive_url_or_id.strip(), "folder"


from app.services.parser import parse_resume_bytes as _parse_resume_bytes, extract_email_from_text


def parse_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF raw bytes."""
    try:
        parsed = _parse_resume_bytes(pdf_bytes, file_name="resume.pdf")
        return parsed.raw_text
    except Exception as e:
        logger.error("Failed to parse PDF bytes: %s", e)
        raise RuntimeError(f"Error parsing PDF content: {e}") from e



def download_public_drive_file(file_id: str) -> bytes | None:
    """Attempt direct public download of a Google Drive file by ID."""
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        req = urllib.request.Request(
            download_url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read()
            if content and b"%PDF" in content[:1024]:
                return content
    except Exception as e:
        logger.warning("Direct public file download failed for %s: %s", file_id, e)
    return None


def fetch_resumes_from_drive(drive_url_or_id: str) -> list[dict[str, Any]]:
    """Fetch PDF resumes from Google Drive folder or public URL.
    
    Strict Real Mode: Returns downloaded PDF resumes or raises RuntimeError.
    """
    drive_id, kind = extract_drive_id_and_kind(drive_url_or_id)
    if not drive_id:
        raise ValueError("No Google Drive URL or Folder/File ID provided.")

    logger.info("Fetching resumes from Google Drive: id=%s, kind=%s", drive_id, kind)

    # 1. Direct public file URL handling (e.g. https://drive.google.com/file/d/XYZ/view)
    if kind == "file" and drive_id:
        pdf_bytes = download_public_drive_file(drive_id)
        if pdf_bytes:
            text = parse_pdf_bytes(pdf_bytes)
            email = extract_email_from_text(text)
            logger.info("Successfully fetched public drive file resume. Email extracted: %s", email)
            return [
                {
                    "id": f"cand_{drive_id[:8]}",
                    "file_name": "Google_Drive_Resume.pdf",
                    "text": text,
                    "email": email,
                    "source": "google_drive_public",
                }
            ]

    # 2. Google Drive API list if credentials present
    settings_token = os.environ.get("GOOGLE_TOKEN_PATH", "token.json")
    if os.path.exists(settings_token):
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaIoBaseDownload
            import io

            creds = Credentials.from_authorized_user_file(settings_token, ["https://www.googleapis.com/auth/drive.readonly"])
            svc = build("drive", "v3", credentials=creds)

            query = f"'{drive_id}' in parents and mimeType = 'application/pdf' and trashed = false"
            results = svc.files().list(q=query, fields="files(id, name)").execute()
            files = results.get("files", [])

            resumes = []
            for f in files:
                req = svc.files().get_media(fileId=f["id"])
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, req)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
                pdf_bytes = fh.getvalue()
                text = parse_pdf_bytes(pdf_bytes)
                email = extract_email_from_text(text)
                resumes.append({
                    "id": f["name"].replace(".pdf", "").replace(" ", "_").lower(),
                    "file_name": f["name"],
                    "text": text,
                    "email": email,
                    "source": "google_drive",
                })
            if resumes:
                return resumes
        except Exception as e:
            logger.error("Google Drive API fetch failed (%s): %s", drive_id, e)
            raise RuntimeError(f"Google Drive API error accessing folder ID '{drive_id}': {e}") from e

    raise RuntimeError(
        f"Unable to access Google Drive PDF from ID/URL '{drive_url_or_id}'. "
        f"Ensure the link is public or place valid 'token.json' credentials in the project root."
    )
