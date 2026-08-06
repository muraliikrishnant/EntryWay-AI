import json
import os

import requests
from crewai.tools import tool

from tools.duckduckgo_jobs import (
    DISQUALIFY_CITIZEN_ONLY_TERMS,
    PERMANENT_RESIDENT_FRIENDLY_TERMS,
    is_entry_level_text,
)
from tools.tracker_tool import is_job_link_active, is_tracked_link, normalize_job_link

API_BASE = "https://jobdataapi.com/api/jobs/"


def _joined_text(title: str, description: str) -> str:
    return f"{title} {description}".lower()


def _eligible_for_permanent_resident(text: str) -> bool:
    has_disqualifier = any(term in text for term in DISQUALIFY_CITIZEN_ONLY_TERMS)
    has_resident_hint = any(term in text for term in PERMANENT_RESIDENT_FRIENDLY_TERMS)
    return (not has_disqualifier) or has_resident_hint


@tool("search_jobdataapi")
def search_jobdataapi(field: str) -> str:
    """
    Search jobdataapi.com for roles matching a field/title. Requires CLEANJOBDATA in the
    environment (an API key for jobdataapi.com). Makes a single request per call to stay
    within the account's tight rate limit, then filters entry-level/permanent-resident
    eligibility locally.
    """
    api_key = os.getenv("CLEANJOBDATA", "").strip()
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
            API_BASE,
            headers={"Authorization": f"Api-Key {api_key}"},
            params={"title": field, "page_size": min(max_results, 25)},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return json.dumps([])

    items: list[dict] = []
    for job in payload.get("results", []):
        link = str(job.get("application_url") or "").strip()
        if not link or is_tracked_link(link, tracked_links):
            continue
        title = str(job.get("title") or "")
        description = str(job.get("description") or "")
        text = _joined_text(title, description)
        if not is_entry_level_text(title, description):
            continue
        if not _eligible_for_permanent_resident(text):
            continue
        if not is_job_link_active(link):
            continue
        company = ((job.get("company") or {}).get("name")) or ""
        items.append(
            {
                "title": title,
                "company": company,
                "link": normalize_job_link(link) or link,
                "snippet": description[:500],
                "source": "jobdataapi",
            }
        )
        if len(items) >= max_results:
            break

    return json.dumps(items, indent=2)
