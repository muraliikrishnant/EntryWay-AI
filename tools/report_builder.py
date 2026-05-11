import datetime as dt
from pathlib import Path
from typing import Any

from tools.interview_utils import extract_json_array, slugify
from tools.outreach_generator import build_outreach_markdown
from tools.tracker_tool import append_job_tracker_row


def _company(item: dict[str, Any]) -> str:
    return str(item.get("company") or item.get("company/agency") or "Unknown").strip()


def _title(item: dict[str, Any]) -> str:
    return str(item.get("title") or "Untitled role").strip()


def _score(item: dict[str, Any]) -> int:
    try:
        return int(float(str(item.get("score", "0")).strip()))
    except ValueError:
        return 0


def _find_job(scored: dict[str, Any], jobs: list[dict[str, Any]]) -> dict[str, Any]:
    scored_title = _title(scored).lower()
    scored_company = _company(scored).lower()
    for job in jobs:
        title = _title(job).lower()
        company = _company(job).lower()
        if scored_title and (scored_title in title or title in scored_title):
            return job
        if scored_company != "unknown" and scored_company and scored_company in company:
            return job
    return {}


def _bullet_list(values: Any) -> str:
    if not values:
        return "- None listed"
    if isinstance(values, str):
        return f"- {values}"
    return "\n".join(f"- {value}" for value in values)


def _extract_cover_letter_paths(text: str) -> list[str]:
    paths = []
    for part in text.split():
        cleaned = part.strip("`.,)")
        if cleaned.startswith("output/cover_letters/") and cleaned.endswith(".txt"):
            paths.append(cleaned)
    return sorted(set(paths))


def build_daily_digest(
    jobs_text: str,
    scored_text: str,
    cover_letters_text: str = "",
    *,
    today: dt.date | None = None,
) -> tuple[str, list[str]]:
    today = today or dt.date.today()
    jobs = extract_json_array(jobs_text) or []
    scored_jobs = extract_json_array(scored_text) or []
    scored_jobs = sorted(
        [job for job in scored_jobs if _score(job) >= 45],
        key=_score,
        reverse=True,
    )
    high_priority = [job for job in scored_jobs if _score(job) >= 65]
    tracker_results = []
    outreach_paths = []

    for scored in scored_jobs:
        original = _find_job(scored, jobs)
        title = _title(scored)
        company = _company(scored)
        location = str(scored.get("location") or original.get("location") or "Not specified")
        apply_link = str(scored.get("apply_link") or original.get("apply_link") or original.get("link") or "")
        if apply_link:
            tracker_results.append(
                append_job_tracker_row(
                    title=title,
                    company=company,
                    location=location,
                    score=str(_score(scored)),
                    apply_link=apply_link,
                    notes=str(scored.get("rationale") or ""),
                    top_gap=", ".join(str(item) for item in scored.get("missing_skills", [])[:2])
                    if isinstance(scored.get("missing_skills"), list)
                    else str(scored.get("missing_skills") or ""),
                    session_date=str(today),
                )
            )

    for scored in high_priority:
        original = _find_job(scored, jobs)
        title = _title(scored)
        company = _company(scored)
        summary = str(original.get("summary") or scored.get("rationale") or title)
        path = Path("output/outreach") / f"{slugify(company)}_{slugify(title)}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(build_outreach_markdown(company, title, summary), encoding="utf-8")
        outreach_paths.append(str(path))

    lines = [
        f"# Job Search Daily Digest - {today}",
        "",
        "## 1) Summary Counts",
        f"- Total roles analyzed: {len(jobs)}",
        f"- Qualified matches (score >= 45): {len(scored_jobs)}",
        f"- High-priority matches (score >= 65): {len(high_priority)}",
        f"- Tracker updates attempted: {len(tracker_results)}",
        "",
        "## 2) Top Matches",
        "| Rank | Role | Company | Score | Location |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for index, scored in enumerate(scored_jobs, start=1):
        original = _find_job(scored, jobs)
        lines.append(
            f"| {index} | {_title(scored)} | {_company(scored)} | {_score(scored)} | "
            f"{scored.get('location') or original.get('location') or 'Not specified'} |"
        )

    lines.extend(["", "## 3) Cover Letters"])
    cover_paths = _extract_cover_letter_paths(cover_letters_text)
    if cover_paths:
        lines.extend(f"- {path}" for path in cover_paths)
    else:
        lines.append("- No cover letters were saved in this run.")

    lines.extend(["", "## 4) Likely Interview Questions"])
    if high_priority:
        for scored in high_priority:
            lines.append(f"### {_title(scored)}")
            lines.append(_bullet_list(scored.get("likely_interview_questions")))
    else:
        lines.append("- No roles scored 65 or higher.")

    lines.extend(["", "## 5) Recurring Skills Gaps"])
    gaps: dict[str, int] = {}
    for scored in scored_jobs:
        missing = scored.get("missing_skills") or []
        if isinstance(missing, str):
            missing = [missing]
        for gap in missing:
            key = str(gap).strip()
            if key:
                gaps[key] = gaps.get(key, 0) + 1
    if gaps:
        for gap, count in sorted(gaps.items(), key=lambda item: (-item[1], item[0]))[:5]:
            lines.append(f"- {gap} ({count})")
    else:
        lines.append("- No recurring gaps listed.")

    lines.extend(["", "## 6) Quick Apply Links"])
    for scored in scored_jobs:
        original = _find_job(scored, jobs)
        link = str(scored.get("apply_link") or original.get("apply_link") or original.get("link") or "")
        if link:
            lines.append(f"- [{_company(scored)} - {_title(scored)}]({link})")

    if outreach_paths:
        lines.extend(["", "## Outreach Files"])
        lines.extend(f"- {path}" for path in outreach_paths)

    return "\n".join(lines).strip() + "\n", outreach_paths
