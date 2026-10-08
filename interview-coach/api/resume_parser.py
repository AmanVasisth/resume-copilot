from pathlib import Path
from io import BytesIO
from pypdf import PdfReader
from docx import Document

def extract_resume_text(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        reader = PdfReader(BytesIO(content))
        return "\n".join((page.extract_text() or "") for page in reader.pages).strip()
    if ext == ".docx":
        doc = Document(BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip()).strip()
    if ext in {".txt", ".md"}:
        return content.decode("utf-8", errors="ignore").strip()
    raise ValueError("Unsupported resume format. Use PDF, DOCX, TXT or MD.")
