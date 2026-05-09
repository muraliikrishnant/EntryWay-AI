import csv
import datetime as dt
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from crewai.tools import tool

TRACKER_PATH = "output/job_tracker.csv"
HEADERS = [
    "date_found",
    "title",
    "company",
    "location",
    "score",
    "status",
    "apply_link",
    "notes",
]
UNAVAILABLE_PAGE_TERMS = (
    "job is no longer available",
    "this job is no longer available",
    "no longer accepting applications",
    "position has been filled",
    "this position has been filled",
    "job has expired",
    "posting has expired",
    "job expired",
    "404 not found",
    "page not found",
    "position is closed",
    "application period has ended",
)


def normalize_job_link(link: str) -> str:
    value = (link or "").strip()
    if not value:
        return ""
    try:
        parts = urlsplit(value)
        query_pairs = []
        for key, val in parse_qsl(parts.query, keep_blank_values=True):
            lk = key.lower()
            if lk.startswith("utm_") or lk in {"ref", "referrer", "source", "src", "campaign", "gh_src"}:
                continue
            query_pairs.append((key, val))
        normalized_query = urlencode(sorted(query_pairs), doseq=True)
        normalized = urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                parts.path.rstrip("/"),
                normalized_query,
                "",
            )
        )
        return normalized
    except Exception:
        return value


def _ensure_tracker() -> None:
    os.makedirs("output", exist_ok=True)
    if not os.path.exists(TRACKER_PATH):
        with open(TRACKER_PATH, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS)
            writer.writeheader()


def load_tracked_links() -> set[str]:
    _ensure_tracker()
    links: set[str] = set()
    with open(TRACKER_PATH, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            raw = (row.get("apply_link") or "").strip()
            normalized = normalize_job_link(raw)
            if normalized:
                links.add(normalized)
            if raw:
                links.add(raw)
    return links


def is_tracked_link(link: str, tracked_links: set[str] | None = None) -> bool:
    if not link:
        return False
    links = tracked_links if tracked_links is not None else load_tracked_links()
    normalized = normalize_job_link(link)
    return link in links or normalized in links


def is_job_link_active(
    link: str,
    *,
    timeout: int | None = None,
    cache: dict[str, bool] | None = None,
) -> bool:
    normalized = normalize_job_link(link)
    if not normalized or normalized in {"n/a", "na"}:
        return False

    if cache is not None and normalized in cache:
        return cache[normalized]

    request_timeout = timeout or int(os.getenv("LINK_CHECK_TIMEOUT_SECONDS", "12"))
    headers = {"User-Agent": "JobSearchAgent/1.0"}

    try:
        head_resp = requests.head(normalized, allow_redirects=True, timeout=request_timeout, headers=headers)
        if head_resp.status_code in {404, 410, 451}:
            if cache is not None:
                cache[normalized] = False
            return False
    except requests.RequestException:
        pass

    try:
        resp = requests.get(
            normalized,
            allow_redirects=True,
            timeout=request_timeout,
            headers=headers,
            stream=True,
        )
        if resp.status_code in {404, 410, 451}:
            if cache is not None:
                cache[normalized] = False
            return False

        content_type = (resp.headers.get("Content-Type") or "").lower()
        if "text/html" in content_type:
            text = resp.text[:8000].lower()
            if any(term in text for term in UNAVAILABLE_PAGE_TERMS):
                if cache is not None:
                    cache[normalized] = False
                return False
    except requests.RequestException:
        if cache is not None:
            cache[normalized] = False
        return False

    if cache is not None:
        cache[normalized] = True
    return True


@tool("append_job_tracker")
def append_job_tracker(
    title: str,
    company: str,
    location: str,
    score: str,
    apply_link: str,
    status: str = "New",
    notes: str = "",
) -> str:
    """
    Append one job row into local CSV tracker.
    """
    _ensure_tracker()
    normalized = normalize_job_link(apply_link)
    if is_tracked_link(apply_link):
        return f"Skipped duplicate: {title} at {company}"
    if not is_job_link_active(normalized or apply_link):
        return f"Skipped inactive link: {title} at {company}"
    with open(TRACKER_PATH, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=HEADERS)
        writer.writerow(
            {
                "date_found": str(dt.date.today()),
                "title": title,
                "company": company,
                "location": location,
                "score": score,
                "status": status,
                "apply_link": normalized or apply_link,
                "notes": notes,
            }
        )
    return f"Saved: {title} at {company}"
