import argparse
import datetime as dt
import os
import time
import traceback

from crewai import Crew, Process
from dotenv import load_dotenv

from agents import hunter, matcher, writer
from tasks import create_tasks
from tools.answer_builder import build_star_feedback
from tools.answer_scorer import build_answer_scorecard
from tools.duckduckgo_jobs import search_entry_level_roles
from tools.interview_utils import read_json, write_json
from tools.mock_interview import generate_mock_questions, save_mock_session
from tools.report_builder import build_daily_digest
from tools.resume_tool import read_my_resume
from tools.weekly_report import generate_weekly_report

load_dotenv()


def _is_transient_llm_error(error: Exception) -> bool:
    message = str(error).lower()
    transient_markers = (
        "error code: 500",
        "internal server error",
        "error code: 502",
        "error code: 503",
        "error code: 504",
        "error code: 429",
        "rate limit",
        "timed out",
        "timeout",
        "connection reset",
        "service unavailable",
    )
    return any(marker in message for marker in transient_markers)


def _kickoff_with_retries(crew: Crew):
    max_attempts = max(1, int(os.getenv("CREW_MAX_RETRIES", "3")))
    base_delay = max(0.1, float(os.getenv("CREW_RETRY_BASE_SECONDS", "2")))
    max_delay = max(base_delay, float(os.getenv("CREW_RETRY_MAX_SECONDS", "30")))

    for attempt in range(1, max_attempts + 1):
        try:
            return crew.kickoff()
        except Exception as exc:
            should_retry = _is_transient_llm_error(exc) and attempt < max_attempts
            if not should_retry:
                raise
            delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
            print(
                f"Transient LLM error on attempt {attempt}/{max_attempts}: {exc}. "
                f"Retrying in {delay:.1f}s..."
            )
            time.sleep(delay)


def run() -> str:
    tasks = create_tasks(hunter, matcher, writer, include_report=False)
    crew = Crew(
        agents=[hunter, matcher, writer],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
    result = _kickoff_with_retries(crew)
    outputs = getattr(result, "tasks_output", []) or []
    if len(outputs) < 2:
        return str(result)
    jobs_text = str(getattr(outputs[0], "raw", "") or "")
    scored_text = str(getattr(outputs[1], "raw", "") or "")
    cover_letters_text = str(getattr(outputs[2], "raw", "") or "") if len(outputs) > 2 else ""
    digest, _outreach_paths = build_daily_digest(jobs_text, scored_text, cover_letters_text)
    return digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test entry-level search tool without running full crew",
    )
    parser.add_argument(
        "--mock-interview",
        action="store_true",
        help="Run an interactive mock interview and save answers under output/sessions",
    )
    parser.add_argument(
        "--answer-builder",
        action="store_true",
        help="Coach one behavioral answer with STAR feedback",
    )
    parser.add_argument(
        "--score-answer",
        action="store_true",
        help="Score one interview answer with the AI answer scorecard",
    )
    parser.add_argument(
        "--add-question",
        action="store_true",
        help="Add a custom practice question to data/custom_questions.json",
    )
    parser.add_argument(
        "--weekly-report",
        action="store_true",
        help="Generate output/weekly_{date}.md from the job tracker",
    )
    args = parser.parse_args()

    today = dt.date.today()
    print(f"\nRunning free job search agent — {today}\n")
    os.makedirs("output", exist_ok=True)
    os.makedirs("output/sessions", exist_ok=True)
    os.makedirs("output/cover_letters", exist_ok=True)
    os.makedirs("output/lessons", exist_ok=True)
    os.makedirs("output/outreach", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    if args.dry_run:
        print(search_entry_level_roles.run("cybersecurity"))
    elif args.add_question:
        question = input("Question: ").strip()
        tag = input("Role tag (e.g. cybersecurity): ").strip()
        difficulty = input("Difficulty (easy/medium/hard): ").strip() or "medium"
        custom_questions = read_json("data/custom_questions.json", [])
        custom_questions.append(
            {"question": question, "tag": tag, "difficulty": difficulty, "source": "custom"}
        )
        write_json("data/custom_questions.json", custom_questions)
        print("Saved to data/custom_questions.json")
    elif args.answer_builder:
        question = input("Interview question: ").strip()
        category = input("Category (default behavioral): ").strip() or "behavioral"
        print("Draft answer. Finish with a blank line:")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        feedback = build_star_feedback(question, "\n".join(lines), category)
        print(feedback)
    elif args.score_answer:
        question = input("Interview question: ").strip()
        keywords = input("Keywords (comma-separated, optional): ").strip()
        print("Answer. Finish with a blank line:")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        keyword_list = [keyword.strip() for keyword in keywords.split(",") if keyword.strip()]
        print(build_answer_scorecard(question, "\n".join(lines), keyword_list or None))
    elif args.mock_interview:
        job_title = input("Job title: ").strip()
        company = input("Company: ").strip()
        print("Job description or summary. Finish with a blank line:")
        jd_lines = []
        while True:
            line = input()
            if not line:
                break
            jd_lines.append(line)
        try:
            resume_text = read_my_resume.run("")
        except Exception:
            resume_text = ""
        jd_summary = "\n".join(jd_lines)
        questions = generate_mock_questions(job_title, company, jd_summary, resume_text)
        answers = []
        for index, question in enumerate(questions, start=1):
            print(f"\n{index}. {question}")
            answer = input("Answer: ").strip()
            answers.append(answer)
        path = save_mock_session(job_title, company, questions, answers)
        print(f"\nSession saved to {path}")
    elif args.weekly_report:
        print(generate_weekly_report.run())
    else:
        try:
            result = run()
            report_path = f"output/report_{today}.md"
            with open(report_path, "w", encoding="utf-8") as file:
                file.write(result)
            print(f"\nDone. Report saved to {report_path}")
        except Exception as exc:
            error_path = f"logs/error_{today}.log"
            with open(error_path, "w", encoding="utf-8") as file:
                file.write(traceback.format_exc())
            print(f"\nAgent failed: {exc}")
            print(f"Error log saved to {error_path}")
