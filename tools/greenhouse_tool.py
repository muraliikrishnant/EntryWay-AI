import csv
import datetime as dt
import json
import os
import re

import requests
from crewai.tools import tool

from tools.duckduckgo_jobs import (
    DISQUALIFY_CITIZEN_ONLY_TERMS,
    PERMANENT_RESIDENT_FRIENDLY_TERMS,
    is_entry_level_text,
)
from tools.tracker_tool import (
    DASHBOARD_DATA_DIR,
    ROLE_CATEGORIES,
    OTHER_CATEGORY,
    TRACKER_PATH,
    is_tracked_link,
    is_tracked_role,
    load_tracked_links,
    load_tracked_role_keys,
    normalize_job_link,
)

API_BASE = "https://api.parse.bot/scraper/83293b68-327f-4cd1-bf90-079591d9fd35"
# Git-tracked so the watchlist is shared between local runs and CI and grows
# over time as new Greenhouse-hosted employers turn up in results.
BOARDS_PATH = "site/data/greenhouse_boards.json"

_BOARD_TOKEN_RE = re.compile(r"(?:job-boards|boards)\.greenhouse\.io/([^/\s,\"']+)", re.IGNORECASE)
_HTML_TAG_RE = re.compile(r"<[^>]+>")

DEFAULT_ROLE_TERMS = tuple(term for terms in ROLE_CATEGORIES.values() for term in terms)
US_LOCATION_HINTS = (
    "united states",
    "usa",
    "u.s.",
    "us-",
    "remote - us",
    "remote, us",
)
NON_US_HINTS = (
    "india",
    "canada",
    "united kingdom",
    "london",
    "germany",
    "france",
    "spain",
    "poland",
    "bulgaria",
    "israel",
    "australia",
    "singapore",
    "japan",
    "brazil",
    "mexico",
    "netherlands",
    "ireland",
)
US_STATE_CODES = frozenset(
    """AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN
    MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA
    WV WI WY DC""".split()
)
US_STATE_NAMES = (
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey",
    "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina",
    "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming",
)
# Two-letter codes are ambiguous (IN = Indiana or India, CA = California or
# Canada), so they're only read as a country when they sit in the trailing
# country slot of a "City, Region, CC" string.
NON_US_COUNTRY_CODES = frozenset(
    """IN FR DE GB UK IE NL ES PT PL BG RO CZ AT CH SE NO DK FI IT GR IL AE
    AU NZ SG JP KR CN HK TW TH VN PH MY ID BR MX AR CL CO PE ZA NG EG KE
    TR UA RS HR SK SI LT LV EE IS LU BE CY MT CR""".split()
)
# "Toronto, ON, CA" can't be settled by the trailing code alone (CA is also
# California), so the province slot disambiguates it.
NON_US_REGION_CODES = frozenset("AB BC MB NB NL NS NT NU ON PE QC SK YT".split())


def _strip_html(text: str) -> str:
    return _HTML_TAG_RE.sub(" ", text or "")


def _csv_paths() -> list[str]:
    paths = [TRACKER_PATH]
    for category in (*ROLE_CATEGORIES.keys(), OTHER_CATEGORY):
        paths.append(f"{DASHBOARD_DATA_DIR}/jobs_{category}.csv")
    return paths


def harvest_board_tokens() -> set[str]:
    """
    Pull Greenhouse board tokens out of apply links we've already collected, so
    every Greenhouse employer the agent finds becomes a board we monitor on
    later runs. Self-maintaining — no hardcoded company list to keep current.
    """
    tokens: set[str] = set()
    for path in _csv_paths():
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", newline="", encoding="utf-8") as file:
                for row in csv.DictReader(file):
                    match = _BOARD_TOKEN_RE.search(row.get("apply_link") or "")
                    if match:
                        token = match.group(1).strip().strip("/")
                        if token and token.lower() != "jobs":
                            tokens.add(token)
        except Exception:
            continue
    return tokens


def load_boards() -> list[str]:
    stored: set[str] = set()
    if os.path.exists(BOARDS_PATH):
        try:
            with open(BOARDS_PATH, "r", encoding="utf-8") as file:
                stored = set(json.load(file) or [])
        except Exception:
            stored = set()

    merged = stored | harvest_board_tokens()
    if merged != stored:
        try:
            os.makedirs(os.path.dirname(BOARDS_PATH), exist_ok=True)
            with open(BOARDS_PATH, "w", encoding="utf-8") as file:
                json.dump(sorted(merged), file, indent=2)
        except Exception:
            pass
    return sorted(merged)


def _select_boards(boards: list[str], limit: int) -> list[str]:
    """
    Rotate which boards get checked, so a capped per-run budget still covers
    every board over consecutive days instead of always re-checking the first N.
    """
    if not boards or limit <= 0 or limit >= len(boards):
        return boards
    start = dt.date.today().toordinal() % len(boards)
    doubled = boards + boards
    return doubled[start:start + limit]


def _is_us_location(location: str) -> bool:
    text = (location or "").strip().lower()
    if not text:
        return True  # unknown location — let the scoring agent judge

    if any(hint in text for hint in NON_US_HINTS):
        return False
    if any(hint in text for hint in US_LOCATION_HINTS):
        return True

    parts = [part.strip() for part in text.split(",") if part.strip()]
    if any(part.upper() in NON_US_REGION_CODES for part in parts):
        return False
    if parts:
        last = parts[-1].upper()
        if last in {"US", "USA"}:
            return True
        # "Bengaluru, KA, IN" / "Paris, IDF, FR": trailing slot is a country.
        if len(parts) >= 3 and len(last) == 2 and last in NON_US_COUNTRY_CODES:
            return False
        # "San Mateo, CA": trailing slot is a state.
        if len(parts) == 2 and last in US_STATE_CODES:
            return True

    if any(name in text for name in US_STATE_NAMES):
        return True
    if re.search(r"(?<!\w)(" + "|".join(US_STATE_CODES).lower() + r")(?!\w)", text):
        return True
    return "remote" in text


def _eligible_for_permanent_resident(text: str) -> bool:
    has_disqualifier = any(term in text for term in DISQUALIFY_CITIZEN_ONLY_TERMS)
    has_resident_hint = any(term in text for term in PERMANENT_RESIDENT_FRIENDLY_TERMS)
    return (not has_disqualifier) or has_resident_hint


def _matches_roles(title: str, role_terms: tuple[str, ...]) -> bool:
    text = (title or "").lower()
    return any(term in text for term in role_terms)


def _fetch_board_jobs(board_token: str) -> list[dict]:
    api_key = os.getenv("PARSE_YC_API_KEY", "").strip()
    if not api_key:
        return []
    try:
        response = requests.get(
            f"{API_BASE}/list_jobs",
            headers={"X-API-Key": api_key},
            params={"board_token": board_token, "content": "true"},
            timeout=40,
        )
        response.raise_for_status()
        data = response.json().get("data") or {}
    except Exception:
        return []
    jobs = data.get("jobs") if isinstance(data, dict) else data
    return jobs or []


@tool("search_greenhouse")
def search_greenhouse(role_keywords: str = "") -> str:
    """
    Search Greenhouse job boards of employers already known to hire for these
    roles. Greenhouse hosts a large share of the postings this agent finds, and
    its board API returns complete, structured listings rather than scraped
    search pages. Board tokens are harvested automatically from previously
    found jobs. role_keywords is an optional comma-separated list of title
    keywords (defaults to the configured solution/architect/devrel roles).
    Costs 1 credit per board checked, so the number of boards per run is
    capped by GREENHOUSE_MAX_BOARDS (default 5) and rotates across runs.
    """
    if not os.getenv("PARSE_YC_API_KEY", "").strip():
        return json.dumps([])

    role_terms = tuple(
        term.strip().lower() for term in (role_keywords or "").split(",") if term.strip()
    ) or DEFAULT_ROLE_TERMS

    boards = load_boards()
    if not boards:
        return json.dumps([])
    limit = max(1, int(os.getenv("GREENHOUSE_MAX_BOARDS", "5")))
    boards = _select_boards(boards, limit)

    tracked_links = load_tracked_links()
    tracked_roles = load_tracked_role_keys()

    items: list[dict] = []
    for board_token in boards:
        for job in _fetch_board_jobs(board_token):
            title = str(job.get("title") or "")
            if not _matches_roles(title, role_terms):
                continue

            link = str(job.get("absolute_url") or "").strip()
            if not link or is_tracked_link(link, tracked_links):
                continue

            location = job.get("location")
            location_name = (
                location.get("name") if isinstance(location, dict) else str(location or "")
            ) or ""
            if not _is_us_location(location_name):
                continue

            body = _strip_html(str(job.get("content") or ""))
            if not is_entry_level_text(title, body):
                continue
            if not _eligible_for_permanent_resident(f"{title} {body}".lower()):
                continue

            company = str(job.get("company_name") or board_token)
            if is_tracked_role(company, title, tracked_roles):
                continue

            items.append(
                {
                    "title": title,
                    "company": company,
                    "location": location_name,
                    "link": normalize_job_link(link) or link,
                    "snippet": body[:500].strip(),
                    "posted": job.get("first_published") or job.get("updated_at") or "",
                    "source": "greenhouse",
                }
            )

    return json.dumps(items, indent=2)
