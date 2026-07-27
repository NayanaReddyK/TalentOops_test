"""Unified Resume Parsing Service (PDF, DOCX, TXT/MD).

Supports parsing raw bytes or file paths into a structured ParsedResume object.
Validates file extensions, size limits, and sanitizes input data.
"""
from __future__ import annotations

import io
import logging
import re
import os
from typing import Any
from pydantic import BaseModel, Field

logger = logging.getLogger("talentops.parser")

_EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
_DEFAULT_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit


class ResumeParseError(Exception):
    """Raised when parsing resume file content fails."""
    pass


class UnsupportedFileTypeError(ResumeParseError):
    """Raised when the uploaded file type is not supported."""
    pass


class FileTooLargeError(ResumeParseError):
    """Raised when file size exceeds maximum permitted limit."""
    pass


class ParsedResume(BaseModel):
    """Structured result of resume parsing."""
    raw_text: str
    file_name: str
    file_type: str
    email: str = ""
    skills: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


def extract_email_from_text(text: str) -> str:
    """Extract candidate email address from resume text."""
    matches = _EMAIL_REGEX.findall(text or "")
    if matches:
        for m in matches:
            if not any(ignore in m.lower() for ignore in ["example.com", "domain.com", "github.com", "w3.org"]):
                return m
        return matches[0]
    return ""


def parse_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from raw PDF bytes using pypdf with fallback for mislabeled text files."""
    for pypdf_log_name in ["pypdf", "pypdf._reader", "pypdf.filters", "pypdf.generic._data_structures"]:
        logging.getLogger(pypdf_log_name).setLevel(logging.ERROR)

    if pdf_bytes.startswith(b"%PDF"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(pdf_bytes))
            extracted = "\n".join((page.extract_text() or "") for page in reader.pages)
            if not extracted.strip():
                raise ResumeParseError("Extracted text from resume is empty or missing")
            return extracted
        except ResumeParseError:
            raise
        except Exception as e:
            logger.warning("pypdf failed to parse PDF bytes: %s", e)
            raise ResumeParseError("Failed to parse PDF content: Invalid or corrupt PDF binary structure") from e

    # Fallback for text files mislabeled with .pdf extension
    try:
        text = pdf_bytes.decode("utf-8", errors="strict")
        if text.strip():
            logger.info("Parsed text file mislabeled with .pdf extension as text")
            return text
    except Exception:
        pass

    raise ResumeParseError("Failed to parse PDF content: Invalid or corrupt PDF binary structure")


def parse_docx_bytes(docx_bytes: bytes) -> str:
    """Extract text from raw DOCX bytes using python-docx or zipfile XML fallback."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(docx_bytes))
        text = "\n".join(p.text for p in doc.paragraphs if p.text)
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    text += "\n" + row_text
        return text
    except ImportError:
        logger.warning("python-docx not installed; attempting XML extraction fallback")
        try:
            import zipfile
            from xml.etree import ElementTree as ET
            with zipfile.ZipFile(io.BytesIO(docx_bytes)) as zf:
                xml_content = zf.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                paragraphs = []
                for p in tree.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
                    texts = [t.text for t in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if t.text]
                    if texts:
                        paragraphs.append("".join(texts))
                return "\n".join(paragraphs)
        except Exception as ex:
            raise ResumeParseError(f"Failed to parse DOCX bytes via XML fallback: {ex}") from ex
    except Exception as e:
        logger.error("Failed to parse DOCX bytes: %s", e)
        raise ResumeParseError(f"Failed to parse DOCX content: {e}") from e


def parse_resume_bytes(
    content: bytes,
    file_name: str = "resume.pdf",
    max_size_bytes: int = _DEFAULT_MAX_SIZE_BYTES,
) -> ParsedResume:
    """Parse resume raw bytes into a ParsedResume object with strict validation."""
    if len(content) > max_size_bytes:
        raise FileTooLargeError(
            f"File size ({len(content)} bytes) exceeds maximum limit of {max_size_bytes} bytes"
        )

    ext = os.path.splitext(file_name)[1].lower() or ".pdf"
    if ext not in _ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"File extension '{ext}' is not supported. Supported extensions: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
        )

    file_type = ext.lstrip(".")

    if file_type == "pdf":
        raw_text = parse_pdf_bytes(content)
    elif file_type == "docx":
        raw_text = parse_docx_bytes(content)
    else:  # txt or md
        try:
            raw_text = content.decode("utf-8", errors="replace")
        except Exception as e:
            raise ResumeParseError(f"Failed to decode text file: {e}") from e

    if not raw_text or not raw_text.strip():
        raise ResumeParseError("Extracted text from resume is empty or missing")

    email = extract_email_from_text(raw_text)

    return ParsedResume(
        raw_text=raw_text,
        file_name=file_name,
        file_type=file_type,
        email=email,
        metadata={"content_length": len(content), "char_count": len(raw_text)}
    )


def parse_resume(path: str) -> ParsedResume:
    """Parse a resume file path."""
    if not os.path.exists(path):
        raise ResumeParseError(f"Resume file path does not exist: {path}")

    with open(path, "rb") as f:
        content = f.read()

    filename = os.path.basename(path)
    return parse_resume_bytes(content, file_name=filename)
