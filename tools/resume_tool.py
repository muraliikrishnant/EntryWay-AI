import os

import pdfplumber
from crewai.tools import tool


@tool("read_my_resume")
def read_my_resume(path: str = "") -> str:
    """
    Extract text from a resume PDF.
    """
    file_path = path or os.getenv("RESUME_PATH", "data/my_resume.pdf")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Resume not found at: {file_path}")

    pages: list[str] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages.append(text.strip())
    if not pages:
        raise ValueError(f"Could not extract text from resume: {file_path}")
    return "\n\n".join(pages)
