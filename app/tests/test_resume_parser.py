"""Tests for resume parsing subsystem (PDF, DOCX, TXT)."""
import os
import pytest
from app.services.parser import (
    parse_resume,
    parse_resume_bytes,
    ParsedResume,
    ResumeParseError,
    UnsupportedFileTypeError,
    FileTooLargeError,
)


def test_parse_txt_bytes():
    raw_content = b"John Doe\nSoftware Engineer\nPython, FastAPI, Postgres\njohn.doe@example.com"
    result = parse_resume_bytes(raw_content, file_name="resume.txt")
    assert isinstance(result, ParsedResume)
    assert "John Doe" in result.raw_text
    assert result.file_type == "txt"
    assert result.email == "john.doe@example.com"


def test_parse_docx_bytes():
    try:
        import docx
    except ImportError:
        pytest.skip("python-docx not installed")

    import io
    doc = docx.Document()
    doc.add_heading("Jane Smith", level=1)
    doc.add_paragraph("Senior Data Scientist - PyTorch, ML, Python")
    doc.add_paragraph("Contact: jane.smith@example.org")

    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    result = parse_resume_bytes(docx_bytes, file_name="jane_resume.docx")
    assert isinstance(result, ParsedResume)
    assert "Jane Smith" in result.raw_text
    assert result.file_type == "docx"
    assert result.email == "jane.smith@example.org"


def test_parse_pdf_bytes():
    pdf_text_content = b"Jane Doe Resume\nSoftware Architect\njane@example.com"
    result = parse_resume_bytes(pdf_text_content, file_name="test.pdf")
    assert isinstance(result, ParsedResume)
    assert result.file_type == "pdf"
    assert "Jane Doe" in result.raw_text


def test_parse_blank_pdf_bytes_raises_error(tmp_path):
    try:
        import pypdf
    except ImportError:
        pytest.skip("pypdf not installed")

    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    pdf_path = str(tmp_path / "blank.pdf")
    with open(pdf_path, "wb") as f:
        writer.write(f)

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    with pytest.raises(ResumeParseError, match="empty or missing"):
        parse_resume_bytes(pdf_bytes, file_name="blank.pdf")


def test_unsupported_file_extension():
    with pytest.raises(UnsupportedFileTypeError):
        parse_resume_bytes(b"some binary content", file_name="resume.exe")


def test_file_size_exceeded():
    large_bytes = b"x" * (11 * 1024 * 1024)  # 11MB
    with pytest.raises(FileTooLargeError):
        parse_resume_bytes(large_bytes, file_name="huge.txt", max_size_bytes=10 * 1024 * 1024)


def test_corrupt_pdf_bytes_raises_parse_error():
    corrupt_pdf = b"%PDF-1.4\ncorrupted header and body data that fails parsing"
    with pytest.raises(ResumeParseError):
        parse_resume_bytes(corrupt_pdf, file_name="bad.pdf")
