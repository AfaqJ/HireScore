from typing import Optional
from pathlib import Path

def parse_txt(data: bytes) -> str:
    return data.decode(errors="ignore")

def parse_pdf(data: bytes) -> str:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=data, filetype="pdf")
        text = "\n".join([page.get_text() for page in doc])
        doc.close()
        return text
    except Exception:
        # fallback to PyPDF
        try:
            from pypdf import PdfReader
            import io
            r = PdfReader(io.BytesIO(data))
            return "\n".join([p.extract_text() or "" for p in r.pages])
        except Exception:
            return ""

def parse_docx(data: bytes) -> str:
    try:
        import io
        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception:
        return ""

def parse_file(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return parse_pdf(data)
    if ext in (".docx",):
        return parse_docx(data)
    if ext in (".txt",):
        return parse_txt(data)
    # naive sniff: try pdf then docx then txt
    out = parse_pdf(data)
    if not out:
        out = parse_docx(data)
    if not out:
        out = parse_txt(data)
    return out
