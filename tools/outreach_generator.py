from pathlib import Path

from crewai.tools import tool

from tools.interview_utils import call_llm, slugify


def build_outreach_markdown(company: str, title: str, job_summary: str) -> str:
    prompt = f"""
Write concise networking outreach for this job.
Company: {company}
Title: {title}
Job summary: {job_summary}

Return markdown with:
## LinkedIn connection message
## Cold email
## Employee types to search
"""
    text = call_llm(prompt)
    if text and "## LinkedIn" in text:
        return text.strip() + "\n"
    return f"""# Outreach - {company} - {title}

## LinkedIn connection message
Hi, I saw the {title} opening at {company} and was interested in the team's work. I am building my career in technical roles and would appreciate any advice on what your team values in strong entry-level candidates.

## Cold email
Subject: Interest in {title} at {company}

Hi,

I am applying for the {title} role at {company}. My background aligns with the role through hands-on technical projects, troubleshooting, and a focus on learning quickly. If you are open to it, I would value any guidance on the team, interview process, or skills that matter most for this opening.

Thank you,
Murali

## Employee types to search
1. Hiring manager or team lead for the role
2. Recruiter supporting technical entry-level hiring
3. Current analyst, engineer, or developer on the target team
"""


@tool("generate_outreach")
def generate_outreach(company: str, title: str, job_summary: str) -> str:
    """
    Generate LinkedIn and email outreach for a top job match and save it under output/outreach.
    """
    output = Path("output/outreach") / f"{slugify(company)}_{slugify(title)}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_outreach_markdown(company, title, job_summary), encoding="utf-8")
    return str(output)
