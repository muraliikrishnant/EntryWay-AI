from crewai import Agent

from llm_config import llm, tool_llm
from tools.answer_builder import build_star_answer
from tools.answer_scorer import score_mock_answer
from tools.cover_letter_tool import save_cover_letter
from tools.duckduckgo_jobs import search_entry_level_roles, search_jobs_ddg
from tools.lesson_generator import generate_lesson
from tools.mock_interview import run_mock_interview
from tools.outreach_generator import generate_outreach
from tools.playbook_tool import get_candidate_playbook
from tools.question_library import get_practice_questions
from tools.remoteok_tool import search_remote_jobs
from tools.resume_tool import read_my_resume
from tools.resume_scorer import score_my_resume
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
    tools=[read_my_resume, score_my_resume, get_practice_questions, get_candidate_playbook],
    llm=llm,
    function_calling_llm=tool_llm,
    verbose=True,
    allow_delegation=False,
)

writer = Agent(
    role="Cover Letter Writer",
    goal="Write concise, tailored cover letters for jobs with score >= 65.",
    backstory="You are a technical career coach focused on high-quality applications.",
    tools=[save_cover_letter, get_candidate_playbook],
    llm=llm,
    function_calling_llm=tool_llm,
    verbose=True,
    allow_delegation=False,
)

outreach = Agent(
    role="Networking Outreach Specialist",
    goal="Generate LinkedIn and email outreach for top job matches.",
    backstory="You craft personalized, concise outreach messages for entry-level candidates.",
    tools=[generate_outreach],
    llm=llm,
    function_calling_llm=tool_llm,
    verbose=True,
    allow_delegation=False,
)

prep_coach = Agent(
    role="Interview Prep Coach",
    goal=(
        "Generate tailored mock interview practice, score answers, build STAR responses, "
        "and create micro-lessons for recurring skill gaps."
    ),
    backstory=(
        "You are a technical interview coach who turns job matches into focused practice."
    ),
    tools=[run_mock_interview, build_star_answer, score_mock_answer, get_practice_questions, generate_lesson],
    llm=llm,
    function_calling_llm=tool_llm,
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
