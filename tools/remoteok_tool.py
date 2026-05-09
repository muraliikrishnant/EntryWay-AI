import json

import requests
from crewai.tools import tool

from tools.duckduckgo_jobs import _eligible_for_permanent_resident
from tools.tracker_tool import (
    is_job_link_active,
    is_tracked_link,
    load_tracked_links,
    normalize_job_link,
)

REMOTEOK_ENTRY_TERMS = (
    "apprentice",
    "apprenticeship",
    "junior",
    "entry",
    "intern",
    "graduate",
    "trainee",
)


def _is_entry_level(record: dict) -> bool:
    text = " ".join(
        [
            str(record.get("title", "")),
            str(record.get("snippet", "")),
            " ".join(record.get("tags") or []),
        ]
    ).lower()
    return any(term in text for term in REMOTEOK_ENTRY_TERMS)


@tool("search_remote_jobs")
def search_remote_jobs(tag: str) -> str:
    """
    Search remote roles via RemoteOK public API.
    """
    response = requests.get(
        f"https://remoteok.com/api?tag={tag}",
        headers={"User-Agent": "JobSearchAgent/1.0"},
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    rows = payload[1:] if isinstance(payload, list) else []
    jobs: list[dict] = []
    tracked_links = load_tracked_links()
    availability_cache: dict[str, bool] = {}
    for row in rows[:8]:
        apply_link = str(row.get("url") or "").strip()
        if is_tracked_link(apply_link, tracked_links):
            continue
        if not is_job_link_active(apply_link, cache=availability_cache):
            continue
        record = {
            "title": row.get("position"),
            "company": row.get("company"),
            "tags": row.get("tags") or [],
            "salary": row.get("salary", "Not listed"),
            "date": (row.get("date") or "")[:10],
            "apply_link": normalize_job_link(apply_link) or apply_link,
            "description": row.get("description", ""),
            "snippet": " ".join(row.get("tags") or []),
            "source": "remoteok",
        }
        if not _is_entry_level(record):
            continue
        if not _eligible_for_permanent_resident(record):
            continue
        jobs.append(record)
    return json.dumps(jobs, indent=2)
