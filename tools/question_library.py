import json
from pathlib import Path

from crewai.tools import tool

from tools.interview_utils import read_json

QUESTION_LIBRARY_PATH = Path("data/question_library.json")
CUSTOM_QUESTIONS_PATH = Path("data/custom_questions.json")


def _normalize_field(field: str) -> str:
    value = field.lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "software": "software_dev",
        "software_development": "software_dev",
        "web": "web_dev",
        "web_development": "web_dev",
        "network": "networking",
        "network_engineering": "networking",
        "security": "cybersecurity",
    }
    return aliases.get(value, value)


def load_question_library() -> dict:
    return read_json(QUESTION_LIBRARY_PATH, {})


def load_custom_questions() -> list[dict]:
    data = read_json(CUSTOM_QUESTIONS_PATH, [])
    return data if isinstance(data, list) else []


def select_questions(field: str, skills: list[str] | None = None, limit: int = 10) -> list[dict]:
    library = load_question_library()
    normalized_field = _normalize_field(field)
    selected: list[dict] = []

    for category in ("behavioral", "situational", normalized_field, "technical"):
        for item in library.get(category, []):
            if isinstance(item, str):
                selected.append(
                    {
                        "question": item,
                        "category": category,
                        "field": normalized_field,
                        "difficulty": "medium",
                        "source": "library",
                    }
                )
            elif isinstance(item, dict) and item.get("question"):
                selected.append({**item, "source": item.get("source", "library")})

    skill_terms = [skill.lower() for skill in skills or []]
    for item in load_custom_questions():
        question = str(item.get("question", ""))
        tag = str(item.get("tag", "")).lower()
        if tag == normalized_field or any(term and term in question.lower() for term in skill_terms):
            selected.append({**item, "category": "custom", "source": "custom"})

    deduped: list[dict] = []
    seen: set[str] = set()
    for item in selected:
        question = str(item.get("question", "")).strip()
        key = question.lower()
        if not question or key in seen:
            continue
        seen.add(key)
        deduped.append({**item, "question": question})
    return deduped[:limit]


@tool("get_practice_questions")
def get_practice_questions(field: str, skills_csv: str = "", limit: str = "10") -> str:
    """
    Return likely interview questions for a role field and optional comma-separated skills.
    """
    skills = [skill.strip() for skill in skills_csv.split(",") if skill.strip()]
    try:
        max_questions = int(limit)
    except ValueError:
        max_questions = 10
    return json.dumps(select_questions(field, skills, max_questions), indent=2)
