import json
import os

from ddgs import DDGS
from crewai.tools import tool

from tools.tracker_tool import is_job_link_active, is_tracked_link, normalize_job_link

ENTRY_LEVEL_TERMS = (
    "entry level",
    "entry-level",
    "associate",
    "junior",
    "jr",
    "level 1",
    "level i",
    "new grad",
    "new graduate",
    "trainee",
)
DISQUALIFY_CITIZEN_ONLY_TERMS = (
    "u.s. citizen",
    "us citizen",
    "usa citizen",
    "citizens only",
    "only citizens",
    "citizenship required",
    "must be a citizen",
    "must be u.s. citizen",
    "must be us citizen",
    "security clearance required",
    "secret clearance required",
    "top secret clearance required",
)
PERMANENT_RESIDENT_FRIENDLY_TERMS = (
    "green card",
    "permanent resident",
    "authorized to work",
    "work authorization",
    "sponsorship not required",
)
NON_JOB_PAGE_TERMS = (
    "blog",
    "finder",
    "how to",
    "what is",
    "salary guide",
    "top ",
    "careerkarma",
    "cybrary.it/blog",
    "reddit.com",
    "youtube.com",
    "wikipedia.org",
)
JOB_PAGE_HINTS = (
    "careers",
    "jobs",
    "job",
    "apply",
    "position",
    "opening",
    "job_url",
)
NON_DIRECT_JOB_URL_PATTERNS = (
    "indeed.com/jobs?",
    "glassdoor.com/Job/",
    "linkedin.com/jobs/search",
    "ziprecruiter.com/jobs-search",
    "search?q=",
    "/blog/",
    "medium.com/",
)
DIRECT_URL_RULES = (
    ("indeed.com", ("/viewjob",)),
    ("linkedin.com", ("/jobs/view/",)),
    ("glassdoor.com", ("joblisting",)),
)


def _joined_text(record: dict) -> str:
    return " ".join(
        [
            str(record.get("title", "")),
            str(record.get("snippet", "")),
            str(record.get("description", "")),
        ]
    ).lower()


def _is_entry_level(record: dict) -> bool:
    text = _joined_text(record)
    return any(term in text for term in ENTRY_LEVEL_TERMS)


def _is_likely_job_posting(record: dict) -> bool:
    text = _joined_text(record)
    link = str(record.get("link") or record.get("apply_link") or "").lower()
    if any(term in text or term in link for term in NON_JOB_PAGE_TERMS):
        return False
    return any(term in text or term in link for term in JOB_PAGE_HINTS)


def _is_direct_job_url(record: dict) -> bool:
    link = str(record.get("link") or record.get("apply_link") or "").lower()
    if not link:
        return False
    if any(pattern in link for pattern in NON_DIRECT_JOB_URL_PATTERNS):
        return False
    for domain, required_markers in DIRECT_URL_RULES:
        if domain in link:
            return any(marker in link for marker in required_markers)
    return True


def _eligible_for_permanent_resident(record: dict) -> bool:
    text = _joined_text(record)
    has_disqualifier = any(term in text for term in DISQUALIFY_CITIZEN_ONLY_TERMS)
    has_resident_hint = any(term in text for term in PERMANENT_RESIDENT_FRIENDLY_TERMS)
    return (not has_disqualifier) or has_resident_hint


def _run_search(
    query: str,
    max_results: int,
    tracked_links: set[str] | None = None,
    availability_cache: dict[str, bool] | None = None,
) -> list[dict]:
    items: list[dict] = []
    seen_links: set[str] = set()
    try:
        with DDGS() as ddgs:
            for result in ddgs.text(query, max_results=max_results):
                record = {
                    "title": result.get("title"),
                    "link": result.get("href"),
                    "snippet": result.get("body", ""),
                    "source": "duckduckgo",
                }
                link = str(record.get("link") or "").strip()
                if not link or link in seen_links:
                    continue
                if is_tracked_link(link, tracked_links):
                    continue
                if not _is_entry_level(record):
                    continue
                if not _is_likely_job_posting(record):
                    continue
                if not _is_direct_job_url(record):
                    continue
                if not _eligible_for_permanent_resident(record):
                    continue
                if not is_job_link_active(link, cache=availability_cache):
                    continue
                seen_links.add(link)
                record["link"] = normalize_job_link(link) or link
                items.append(record)
    except Exception:
        return []
    return items


@tool("search_jobs_ddg")
def search_jobs_ddg(query: str) -> str:
    """
    Search jobs using DuckDuckGo text search, no API key required.
    """
    max_results = int(os.getenv("TOP_N_JOBS", "10"))
    full_query = f"{query} entry level OR junior OR associate OR \"level 1\""
    tracked_links: set[str] = set()
    availability_cache: dict[str, bool] = {}
    try:
        from tools.tracker_tool import load_tracked_links

        tracked_links = load_tracked_links()
    except Exception:
        tracked_links = set()
    return json.dumps(
        _run_search(
            full_query,
            max_results,
            tracked_links=tracked_links,
            availability_cache=availability_cache,
        ),
        indent=2,
    )


@tool("search_entry_level_roles")
def search_entry_level_roles(field: str) -> str:
    """
    Search entry-level roles across the internet for a field.
    Excludes obvious citizen-only roles and keeps permanent-resident-friendly results.
    """
    max_results = max(5, int(os.getenv("TOP_N_JOBS", "10")))
    queries = [
        f"{field} entry level",
        f"{field} associate",
        f"{field} junior",
        f"{field} level 1",
        f"{field} entry level not citizen only",
    ]
    internet_sources = [
        "",
        "site:linkedin.com",
        "site:indeed.com",
        "site:glassdoor.com",
        "site:ziprecruiter.com",
        "site:lever.co",
        "site:greenhouse.io",
        "site:workdayjobs.com",
    ]
    merged: list[dict] = []
    seen_links: set[str] = set()
    tracked_links: set[str] = set()
    availability_cache: dict[str, bool] = {}
    try:
        from tools.tracker_tool import load_tracked_links

        tracked_links = load_tracked_links()
    except Exception:
        tracked_links = set()
    for query in queries:
        for source_hint in internet_sources:
            full_query = f"{query} {source_hint}".strip()
            for record in _run_search(
                full_query,
                max_results,
                tracked_links=tracked_links,
                availability_cache=availability_cache,
            ):
                link = str(record.get("link") or "").strip()
                if not link or link in seen_links:
                    continue
                seen_links.add(link)
                merged.append(record)
    return json.dumps(merged, indent=2)
