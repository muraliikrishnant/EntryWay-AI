import json
import os

import requests
from crewai.tools import tool

from tools.duckduckgo_jobs import _eligible_for_permanent_resident, _is_apprenticeship
from tools.tracker_tool import (
    is_job_link_active,
    is_tracked_link,
    load_tracked_links,
    normalize_job_link,
)


@tool("search_usajobs")
def search_usajobs(keyword: str) -> str:
    """
    Search USAJobs for federal opportunities.
    """
    api_key = os.getenv("USAJOBS_API_KEY")
    user_email = os.getenv("USAJOBS_EMAIL")
    if not api_key or not user_email:
        raise ValueError("Missing USAJOBS_API_KEY or USAJOBS_EMAIL in .env")

    headers = {
        "Host": "data.usajobs.gov",
        "User-Agent": user_email,
        "Authorization-Key": api_key,
    }
    params = {
        "Keyword": keyword,
        "ResultsPerPage": int(os.getenv("TOP_N_JOBS", "10")),
        "WhoMayApply": "public",
        "SortField": "OpenDate",
        "SortDirection": "Desc",
    }

    response = requests.get(
        "https://data.usajobs.gov/api/search",
        headers=headers,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    items = response.json().get("SearchResult", {}).get("SearchResultItems", [])
    jobs: list[dict] = []
    tracked_links = load_tracked_links()
    availability_cache: dict[str, bool] = {}
    for item in items:
        d = item.get("MatchedObjectDescriptor", {})
        rem = (d.get("PositionRemuneration") or [{}])[0]
        apply_link = str((d.get("ApplyURI") or ["N/A"])[0] or "").strip()
        if is_tracked_link(apply_link, tracked_links):
            continue
        if not is_job_link_active(apply_link, cache=availability_cache):
            continue
        record = {
            "title": d.get("PositionTitle"),
            "agency": d.get("OrganizationName"),
            "location": d.get("PositionLocationDisplay"),
            "salary_min": rem.get("MinimumRange"),
            "salary_max": rem.get("MaximumRange"),
            "close_date": (d.get("ApplicationCloseDate") or "")[:10],
            "apply_link": normalize_job_link(apply_link) or apply_link,
            "snippet": d.get("QualificationSummary", ""),
            "source": "usajobs",
        }
        if not _is_apprenticeship(record):
            continue
        if not _eligible_for_permanent_resident(record):
            continue
        jobs.append(record)
    return json.dumps(jobs, indent=2)
