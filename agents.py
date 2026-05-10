from crewai import Agent

from llm_config import llm, tool_llm
from tools.duckduckgo_jobs import search_entry_level_roles, search_jobs_ddg
from tools.remoteok_tool import search_remote_jobs
from tools.resume_tool import read_my_resume
from tools.tracker_tool import append_job_tracker
from tools.usajobs_tool import search_usajobs

all_search_tools = [
    search_entry_level_roles,
    search_jobs_ddg,
    search_remote_jobs,
    search_usajobs,
]

hunter = Agent(
    role="Job Hunter",
    goal=(
        "Find entry-level roles in cybersecurity, software development, "
        "web development, and network engineering from across the internet."
    ),
    backstory=(
        "You search internet-wide job sources and keep only roles suitable for "
        "a U.S. permanent resident (non-citizen)."
    ),
    tools=all_search_tools,
    llm=llm,
    function_calling_llm=tool_llm,
    verbose=True,
    allow_delegation=False,
)

matcher = Agent(
    role="Resume Match Analyst",
    goal="Score entry-level jobs from 0-100 against the candidate resume with clear gap analysis.",
    backstory=(
        "You are an ATS and hiring specialist focused on entry-level hiring and "
        "work-authorization constraints."
    ),
    tools=[read_my_resume],
    llm=llm,
    function_calling_llm=tool_llm,
    verbose=True,
    allow_delegation=False,
)

writer = Agent(
    role="Cover Letter Writer",
    goal="Write concise, tailored cover letters for jobs with score >= 65.",
    backstory="You are a technical career coach focused on high-quality applications.",
    llm=llm,
    verbose=True,
    allow_delegation=False,
)

reporter = Agent(
    role="Daily Report Builder",
    goal="Produce a ranked digest and save entry-level matches to the local CSV tracker.",
    backstory="You turn search output into a practical daily action list.",
    tools=[append_job_tracker],
    llm=llm,
    function_calling_llm=tool_llm,
    verbose=True,
    allow_delegation=False,
)
