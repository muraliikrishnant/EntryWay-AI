import datetime as dt
from pathlib import Path

import pandas as pd
from crewai.tools import tool

from tools.tracker_tool import TRACKER_PATH


def build_weekly_report() -> str:
    path = Path(TRACKER_PATH)
    today = dt.date.today()
    if not path.exists():
        return f"# Weekly Progress Report - {today}\n\nNo tracker data found yet.\n"

    df = pd.read_csv(path)
    if df.empty:
        return f"# Weekly Progress Report - {today}\n\nNo tracked jobs yet.\n"

    for column in ("mock_score", "star_score"):
        if column in df:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    top_gaps = []
    if "top_gap" in df:
        top_gaps = [
            f"- {gap}: {count} occurrence(s)"
            for gap, count in df["top_gap"].dropna().astype(str).value_counts().head(3).items()
            if gap.strip()
        ]

    mock_avg = df["mock_score"].dropna().mean() if "mock_score" in df else float("nan")
    star_avg = df["star_score"].dropna().mean() if "star_score" in df else float("nan")
    schedule = [
        "1. Run one mock interview for the highest-scoring open role.",
        "2. Rewrite two weak STAR answers and rescore them.",
        "3. Practice the top recurring technical gap for 30 minutes.",
    ]
    report = [
        f"# Weekly Progress Report - {today}",
        "",
        "## Snapshot",
        f"- Jobs tracked: {len(df)}",
        f"- Average mock score: {mock_avg:.1f}" if pd.notna(mock_avg) else "- Average mock score: no sessions scored yet",
        f"- Average STAR score: {star_avg:.1f}" if pd.notna(star_avg) else "- Average STAR score: no STAR answers scored yet",
        "",
        "## Persisting Gaps",
        *(top_gaps or ["- No recurring gaps recorded yet."]),
        "",
        "## Recommended Practice Schedule",
        *schedule,
        "",
    ]
    return "\n".join(report)


@tool("generate_weekly_report")
def generate_weekly_report() -> str:
    """
    Generate a markdown weekly progress report from output/job_tracker.csv.
    """
    output = Path("output") / f"weekly_{dt.date.today()}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_weekly_report(), encoding="utf-8")
    return str(output)
