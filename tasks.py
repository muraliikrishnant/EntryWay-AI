import datetime as dt
import os

from crewai import Task

DEFAULT_ROLES = [
    "solution engineer / solutions engineer",
    "solution architect / solutions architect",
    "developer relations / developer advocate",
]


def _search_roles() -> list[str]:
    keywords = os.getenv("SEARCH_KEYWORDS", "").strip()
    if not keywords:
        return DEFAULT_ROLES
    return [term.strip() for term in keywords.split(",") if term.strip()] or DEFAULT_ROLES


def create_tasks(hunter, matcher, writer, reporter=None, outreach=None, include_report: bool = True):
    today = dt.date.today()
    roles = _search_roles()
    role_lines = "\n".join(
        f"{index}) {role} entry level / junior / associate / level 1"
        for index, role in enumerate(roles, start=1)
    )
    t1 = Task(
        description=f"""
Search internet-wide for entry-level roles posted recently (prefer last 10 days):
{role_lines}

You must:
- call search_entry_level_roles once per role FIRST — this is the primary tool. It runs
  site-scoped queries against employer ATS hosts (greenhouse.io, lever.co, workdayjobs.com,
  etc.) and returns individual job postings.
- use search_jobs_ddg only as a secondary fallback, and keep its queries SIMPLE (e.g.
  "junior solutions engineer greenhouse"). Complex boolean queries with quotes, OR, minus
  terms and after: dates mostly return aggregator search-listing pages (Indeed/LinkedIn
  search results), which are correctly discarded as non-postings and yield nothing.
- also call search_jobdataapi once per role (it has a very tight rate limit, so call it
  sparingly — one query per role, not per variant)
- also call search_yc_jobs once (role_category="software-engineer") to surface YC-backed
  startup roles — it only supports broad role categories, not free-text search, so call it
  once total for this task, not once per role
- keep search scope to U.S.-wide and remote-friendly roles
- only keep roles requiring a maximum of 1 year of professional experience (0-1 YOE);
  exclude any role that asks for 2+ years of experience or "senior"/"mid-level" roles
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
Read the candidate resume first using the configured RESUME_PATH. Do not pass a placeholder
path such as resume.pdf to read_my_resume.
Then score each job from Task 1 using:
- degree and training alignment
- relevant technical skill overlap
- missing skills list
- location/remote compatibility
- permanent-resident work-authorization compatibility confidence
- likely interview questions from the question library for jobs scoring >= 65

Output each role with score 0-100 and 2-sentence rationale.
Keep jobs scoring >= 45.
""",
        expected_output=(
            "A JSON array containing each qualifying job with score, rationale, "
            "strengths, missing_skills, and likely_interview_questions for score >= 65 roles."
        ),
        agent=matcher,
        context=[t1],
    )

    t3 = Task(
        description="""
Load the candidate playbook first and apply its guidance.
For each role with score >= 65:
1. Extract the top 10 ATS keywords from the job description.
2. Write a tailored cover letter that naturally embeds those keywords.
3. Keep the existing candidate cover letter structure: 3 short paragraphs, <= 300 words,
   specific role/company references, technical strengths, motivation, and U.S. permanent
   resident work authorization.
4. Save each letter by calling save_cover_letter with the company, title, and final letter.
""",
        expected_output=(
            "A list of cover letters keyed by job title/company, ATS keywords, and saved file paths "
            "for all jobs with score >= 65."
        ),
        agent=writer,
        context=[t2],
    )

    tasks = [t1, t2, t3]

    if not include_report:
        return tasks

    if reporter is None:
        raise ValueError("reporter is required when include_report=True")

    t4 = Task(
        description=f"""
Create markdown digest titled: Job Search Daily Digest — {today}
Sections:
1) Summary counts
2) Top matches sorted by score desc
3) Cover letters for score >= 65
4) Likely interview questions for score >= 65 roles
5) Recurring skills gaps
6) Quick apply links

For each score >= 45 role, call append_job_tracker with details so output is persisted to CSV.
You MUST call append_job_tracker once for each qualifying role before writing the final report.
""",
        expected_output=(
            "A markdown daily digest report with summary, ranked matches, cover letters, "
            "skills gaps, and quick apply links."
        ),
        agent=reporter,
        context=[t1, t2, t3],
    )

    tasks.append(t4)

    if outreach is not None:
        t5 = Task(
            description="""
For each role with score >= 65, generate networking outreach:
1. A concise LinkedIn connection message.
2. A concise cold email template.
3. Three employee types to search at that company.

Call generate_outreach for every score >= 65 role so files are saved under output/outreach/.
""",
            expected_output=(
                "A list of outreach file paths for every score >= 65 role."
            ),
            agent=outreach,
            context=[t2, t4],
        )
        tasks.append(t5)

    return tasks
