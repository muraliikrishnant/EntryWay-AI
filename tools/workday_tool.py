import os

import requests

API_BASE = "https://api.parse.bot/scraper/75f11f0d-6134-48ef-bbf8-0fd628bcc2c4"


def is_workday_link(link: str) -> bool:
    return "myworkdayjobs.com" in (link or "").lower()


def get_workday_job(job_url: str) -> dict | None:
    """
    Fetch structured job details from Workday's (JS-rendered) career pages via
    the parse.bot Workday API. Returns None on any failure or missing key so
    callers can fall back to the generic HTML-based liveness check.
    """
    api_key = os.getenv("PARSE_YC_API_KEY", "").strip()
    if not api_key or not job_url:
        return None
    try:
        response = requests.get(
            f"{API_BASE}/get_job",
            headers={"X-API-Key": api_key},
            params={"job_url": job_url},
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None
    return payload.get("data")


def is_workday_job_active(job_url: str) -> bool | None:
    """
    Returns True/False based on the Workday API's can_apply flag, or None if
    the lookup failed (caller should fall back to the generic check).
    """
    details = get_workday_job(job_url)
    if details is None:
        return None
    return bool(details.get("can_apply"))
