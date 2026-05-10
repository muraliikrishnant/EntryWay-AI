import argparse
import datetime as dt
import os
import traceback

from crewai import Crew, Process
from dotenv import load_dotenv

from agents import hunter, matcher, reporter, writer
from tasks import create_tasks
from tools.duckduckgo_jobs import search_entry_level_roles

load_dotenv()


def run() -> str:
    crew = Crew(
        agents=[hunter, matcher, writer, reporter],
        tasks=create_tasks(hunter, matcher, writer, reporter),
        process=Process.sequential,
        verbose=True,
    )
    return str(crew.kickoff())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test entry-level search tool without running full crew",
    )
    args = parser.parse_args()

    today = dt.date.today()
    print(f"\nRunning free job search agent — {today}\n")
    os.makedirs("output", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    if args.dry_run:
        print(search_entry_level_roles.run("cybersecurity"))
    else:
        try:
            result = run()
            report_path = f"output/report_{today}.md"
            with open(report_path, "w", encoding="utf-8") as file:
                file.write(result)
            print(f"\nDone. Report saved to {report_path}")
        except Exception as exc:
            error_path = f"logs/error_{today}.log"
            with open(error_path, "w", encoding="utf-8") as file:
                file.write(traceback.format_exc())
            print(f"\nAgent failed: {exc}")
            print(f"Error log saved to {error_path}")
