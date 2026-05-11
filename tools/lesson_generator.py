from pathlib import Path

from crewai.tools import tool

from tools.interview_utils import call_llm, slugify


def generate_lesson_markdown(skill_gap: str) -> str:
    prompt = f"""
Write a concise 300-word interview prep lesson for: {skill_gap}
Format:
## What it is
## Why interviewers ask
## Model STAR answer
## 3 Practice questions
"""
    text = call_llm(prompt)
    if text and "## What it is" in text:
        return text.strip() + "\n"
    return f"""# {skill_gap} Interview Prep

## What it is
{skill_gap} is a capability employers expect candidates to explain in practical terms, not just define.

## Why interviewers ask
Interviewers ask about it to confirm that you understand the concept, know when to use it, and can connect it to real project decisions.

## Model STAR answer
Situation: In a technical project, I needed to close a gap related to {skill_gap}.
Task: My goal was to learn the core workflow and apply it in a way that improved the project.
Action: I reviewed documentation, built a small proof of concept, tested the result, and documented what changed.
Result: I gained a repeatable approach and could explain the tradeoffs clearly in future work.

## 3 Practice questions
1. What is {skill_gap}, and when would you use it?
2. Tell me about a time you had to learn {skill_gap} quickly.
3. What mistakes should a beginner avoid with {skill_gap}?
"""


@tool("generate_lesson")
def generate_lesson(skill_gap: str) -> str:
    """
    Generate and save a markdown micro-lesson for a recurring skill gap.
    """
    output = Path("output/lessons") / f"{slugify(skill_gap)}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    markdown = generate_lesson_markdown(skill_gap)
    output.write_text(markdown, encoding="utf-8")
    return str(output)
