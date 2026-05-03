from io import BytesIO

from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract raw text from an uploaded PDF resume."""
    reader = PdfReader(BytesIO(file_bytes))

    pages_text: list[str] = []
    for page in reader.pages:
        pages_text.append(page.extract_text() or "")

    result = "\n\n".join(pages_text).strip()

    if not result:
        raise ValueError("Could not extract text from PDF")

    return result
