import datetime as dt
import os

from crewai import Crew, Process
from dotenv import load_dotenv

from agents import hunter, matcher, reporter, writer
from tasks import create_tasks

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
    today = dt.date.today()
    print(f"\nRunning free job search agent — {today}\n")
    result = run()

    os.makedirs("output", exist_ok=True)
    report_path = f"output/report_{today}.md"
    with open(report_path, "w", encoding="utf-8") as file:
        file.write(result)

    print(f"\nDone. Report saved to {report_path}")
