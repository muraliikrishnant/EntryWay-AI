import datetime as dt

from crewai import Task


def create_tasks(hunter, matcher, writer, reporter, outreach=None):
    today = dt.date.today()
    t1 = Task(
        description="""
Search internet-wide for entry-level roles posted recently (prefer last 10 days):
1) cybersecurity entry level / junior / associate / level 1
2) software development entry level / junior / associate / level 1
3) web development entry level / junior / associate / level 1
4) network engineer entry level / junior / associate / level 1

You must:
- prioritize web-wide sources (LinkedIn, Indeed, Glassdoor, employer ATS pages, job boards)
- keep search scope to U.S.-wide and remote-friendly roles
- exclude senior/unrelated roles
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

    tasks = [t1, t2, t3, t4]

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
