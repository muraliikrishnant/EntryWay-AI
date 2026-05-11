import datetime as dt
import json
from pathlib import Path

from crewai.tools import tool

from tools.answer_scorer import build_answer_scorecard
from tools.interview_utils import call_llm, extract_json_object, extract_keywords, slugify, write_json
from tools.question_library import select_questions

SESSION_DIR = Path("output/sessions")


def generate_mock_questions(
    job_title: str,
    company: str,
    jd_summary: str,
    resume_text: str = "",
    count: int = 7,
) -> list[str]:
    field = "software_dev"
    lower = f"{job_title} {jd_summary}".lower()
    if "cyber" in lower or "security" in lower:
        field = "cybersecurity"
    elif "network" in lower:
        field = "networking"
    elif "web" in lower or "frontend" in lower or "front-end" in lower:
        field = "web_dev"

    keywords = extract_keywords(jd_summary, limit=8)
    prompt = f"""
Generate {count} interview questions for {job_title} at {company}.
Use the job description and resume to tailor the questions.
Return strict JSON: {{"questions": ["...", "..."]}}

Job description:
{jd_summary}

Resume excerpt:
{resume_text[:1200]}
"""
    parsed = extract_json_object(call_llm(prompt) or "")
    if parsed and isinstance(parsed.get("questions"), list):
        questions = [str(item).strip() for item in parsed["questions"] if str(item).strip()]
        if questions:
            return questions[:count]

    library_questions = select_questions(field, keywords, count)
    questions = [item["question"] for item in library_questions]
    while len(questions) < count:
        skill = keywords[len(questions) % len(keywords)] if keywords else job_title
        questions.append(f"Tell me about a time you used {skill} to solve a practical problem.")
    return questions[:count]


def save_mock_session(
    job_title: str,
    company: str,
    questions: list[str],
    answers: list[str] | None = None,
    keywords: list[str] | None = None,
) -> Path:
    today = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SESSION_DIR / f"{today}_{slugify(company)}_{slugify(job_title)}.json"
    scorecards = []
    if answers:
        for question, answer in zip(questions, answers):
            scorecards.append(build_answer_scorecard(question, answer, keywords))
    write_json(
        path,
        {
            "created_at": dt.datetime.now().isoformat(timespec="seconds"),
            "job_title": job_title,
            "company": company,
            "questions": questions,
            "answers": answers or [],
            "scorecards": scorecards,
        },
    )
    return path


@tool("run_mock_interview")
def run_mock_interview(job_title: str, company: str, jd_summary: str, resume_text: str = "") -> str:
    """
    Generate tailored mock interview questions and save a session shell under output/sessions.
    """
    questions = generate_mock_questions(job_title, company, jd_summary, resume_text)
    path = save_mock_session(job_title, company, questions)
    return json.dumps({"session_path": str(path), "questions": questions}, indent=2)
