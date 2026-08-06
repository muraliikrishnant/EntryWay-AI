import json
import os

import requests
from crewai.tools import tool

from tools.duckduckgo_jobs import (
    DISQUALIFY_CITIZEN_ONLY_TERMS,
    ENTRY_LEVEL_TERMS,
    EXPERIENCE_DISQUALIFY_TERMS,
    PERMANENT_RESIDENT_FRIENDLY_TERMS,
)
from tools.tracker_tool import is_job_link_active, is_tracked_link, normalize_job_link

API_BASE = "https://api.parse.bot/scraper/303993f2-6efa-4ab4-9310-f02643b002a4"
# The API only supports broad role categories (no free-text keyword search), so
# we pick the closest match per default role and fall back to software-engineer.
ROLE_CATEGORY_HINTS = {
    "solution_engineering": "software-engineer",
    "solutions_architect": "software-engineer",
    "developer_relations": "product",
}


def _joined_text(title: str, location: str) -> str:
    return f"{title} {location}".lower()


def _is_entry_level(text: str) -> bool:
    if not any(term in text for term in ENTRY_LEVEL_TERMS):
        return False
    return not any(term in text for term in EXPERIENCE_DISQUALIFY_TERMS)


def _eligible_for_permanent_resident(text: str) -> bool:
    has_disqualifier = any(term in text for term in DISQUALIFY_CITIZEN_ONLY_TERMS)
    has_resident_hint = any(term in text for term in PERMANENT_RESIDENT_FRIENDLY_TERMS)
    return (not has_disqualifier) or has_resident_hint


@tool("search_yc_jobs")
def search_yc_jobs(role_category: str = "software-engineer") -> str:
    """
    Search YC-backed startup job listings (via the Y Combinator API on parse.bot).
    Requires PARSE_YC_API_KEY in the environment. role_category must be one of:
    software-engineer, designer, product, science. Makes a single request per call
    to stay within the account's credit budget, then filters entry-level/
    permanent-resident eligibility locally, same as the other job sources.
    """
    api_key = os.getenv("PARSE_YC_API_KEY", "").strip()
    if not api_key:
        return json.dumps([])

    max_results = max(5, int(os.getenv("TOP_N_JOBS", "10")))
    tracked_links: set[str] = set()
    try:
        from tools.tracker_tool import load_tracked_links

        tracked_links = load_tracked_links()
    except Exception:
        tracked_links = set()

    try:
        response = requests.get(
            f"{API_BASE}/search_jobs",
            headers={"X-API-Key": api_key},
            params={"role": role_category or "software-engineer"},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return json.dumps([])

    jobs = payload.get("data", payload) if isinstance(payload, dict) else payload
    if isinstance(jobs, dict):
        jobs = jobs.get("jobs") or jobs.get("hits") or []

    items: list[dict] = []
    for job in jobs or []:
        link = str(job.get("url") or job.get("apply_url") or job.get("link") or "").strip()
        if not link or is_tracked_link(link, tracked_links):
            continue
        title = str(job.get("title") or "")
        location = str(job.get("location") or "")
        text = _joined_text(title, location)
        if not _is_entry_level(text):
            continue
        if not _eligible_for_permanent_resident(text):
            continue
        if not is_job_link_active(link):
            continue
        company = str(job.get("company_name") or job.get("company") or "")
        items.append(
            {
                "title": title,
                "company": company,
                "location": location,
                "link": normalize_job_link(link) or link,
                "snippet": f"YC batch {job.get('company_batch') or job.get('batch') or ''}".strip(),
                "source": "yc_jobs",
            }
        )
        if len(items) >= max_results:
            break

    return json.dumps(items, indent=2)
