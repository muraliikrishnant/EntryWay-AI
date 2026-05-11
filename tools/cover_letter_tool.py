from pathlib import Path

from crewai.tools import tool

from tools.interview_utils import slugify


@tool("save_cover_letter")
def save_cover_letter(company: str, title: str, letter_text: str) -> str:
    """
    Save a tailored cover letter under output/cover_letters/{company}_{title}.txt.
    """
    output = Path("output/cover_letters") / f"{slugify(company)}_{slugify(title)}.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(letter_text.strip() + "\n", encoding="utf-8")
    return str(output)
