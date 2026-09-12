"""
Document Parser Utility
Supports extracting structured text from PDFs (using pypdf) and Markdown/Text files.
Splits by Markdown headers, numbered sections (e.g. 1. Cryptography), or paragraph chunks.
"""
import os
import re
from typing import List, Dict, Any
from pypdf import PdfReader

def parse_document(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    filename = os.path.basename(file_path)

    if ext == ".pdf":
        return _parse_pdf(file_path, filename)
    else:
        return _parse_text_or_markdown(file_path, filename)

def _parse_pdf(file_path: str, filename: str) -> Dict[str, Any]:
    reader = PdfReader(file_path)
    pages = []
    full_text_parts = []

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        text = page.extract_text() or ""
        pages.append({"page_number": page_num, "text": text})
        full_text_parts.append(f"--- [Page {page_num}] ---\n" + text)

    full_text = "\n\n".join(full_text_parts)
    sections = _split_into_sections(full_text)

    return {
        "filename": filename,
        "extension": ".pdf",
        "full_text": full_text,
        "pages": pages,
        "sections": sections
    }

def _parse_text_or_markdown(file_path: str, filename: str) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        full_text = f.read()

    sections = _split_into_sections(full_text)
    pages = [{"page_number": 1, "text": full_text}]

    return {
        "filename": filename,
        "extension": os.path.splitext(file_path)[1].lower(),
        "full_text": full_text,
        "pages": pages,
        "sections": sections
    }

def _split_into_sections(text: str) -> List[Dict[str, str]]:
    lines = text.split("\n")
    sections = []
    current_title = "Overview"
    current_lines = []

    header_pattern = re.compile(r"^(?:#+\s+|(?:\d+\.\s+[A-Za-z])|(?:Executive Summary))")

    for line in lines:
        stripped = line.strip()
        if header_pattern.match(stripped):
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    sections.append({
                        "title": current_title,
                        "content": content
                    })
                current_lines = []
            current_title = stripped.lstrip("#").strip()
        else:
            current_lines.append(line)

    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append({
                "title": current_title,
                "content": content
            })

    return sections