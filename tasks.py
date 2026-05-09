import datetime as dt

from crewai import Task


def create_tasks(hunter, matcher, writer, reporter):
    today = dt.date.today()
    t1 = Task(
        description="""
Search internet-wide for apprenticeship-only roles posted recently (prefer last 10 days):
1) cybersecurity apprenticeship
2) software development apprenticeship
3) web development apprenticeship
4) network engineer apprenticeship

You must:
- prioritize web-wide sources (LinkedIn, Indeed, Glassdoor, employer ATS pages, job boards)
- keep search scope to U.S.-wide and remote-friendly roles
- exclude internships, new-grad, junior, and non-apprenticeship roles
- exclude jobs requiring U.S. citizenship only
- keep jobs that are clearly friendly to permanent residents or do not impose citizenship-only constraints
- skip any role whose link already exists in output/job_tracker.csv
- verify each apply link is still active before including it

Return merged, deduplicated list with title, company/agency, location, salary if present,
summary, source, and application link.
""",
        expected_output=(
            "A deduplicated JSON array of jobs with title, company/agency, location, "
            "salary, summary, source, and apply_link."
        ),
        agent=hunter,
    )

    t2 = Task(
        description="""
Read the candidate resume first.
Then score each job from Task 1 using:
- degree and training alignment
- relevant technical skill overlap
- missing skills list
- location/remote compatibility
- permanent-resident work-authorization compatibility confidence

Output each role with score 0-100 and 2-sentence rationale.
Keep jobs scoring >= 45.
""",
        expected_output=(
            "A JSON array containing each qualifying job with score, rationale, "
            "strengths, and missing_skills."
        ),
        agent=matcher,
        context=[t1],
    )

    t3 = Task(
        description="""
For each role with score >= 65, write a tailored cover letter:
- 3 short paragraphs
- <= 300 words
- specific role/company references
- technical strengths and motivation
- mention the candidate is a U.S. permanent resident with work authorization
""",
        expected_output=(
            "A list of cover letters keyed by job title/company for all jobs with score >= 65."
        ),
        agent=writer,
        context=[t2],
    )

    t4 = Task(
        description=f"""
Create markdown digest titled: Job Search Daily Digest — {today}
Sections:
1) Summary counts
2) Top matches sorted by score desc
3) Cover letters for score >= 65
4) Recurring skills gaps
5) Quick apply links

For each score >= 45 role, call append_job_tracker with details so output is persisted to CSV.
""",
        expected_output=(
            "A markdown daily digest report with summary, ranked matches, cover letters, "
            "skills gaps, and quick apply links."
        ),
        agent=reporter,
        context=[t1, t2, t3],
    )

    return [t1, t2, t3, t4]
