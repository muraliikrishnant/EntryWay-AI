import json
from pathlib import Path

from crewai.tools import tool

from tools.answer_scorer import build_answer_scorecard
from tools.interview_utils import call_llm, extract_json_object, read_json, sentence_count, slugify, write_json, words

STAR_ANSWERS_PATH = Path("data/star_answers.json")


def _heuristic_star_scores(draft: str) -> dict:
    lower = draft.lower()
    wc = len(words(draft))
    return {
        "s_score": min(10, 3 + (2 if any(term in lower for term in ("when", "while", "context", "situation")) else 0) + (2 if wc > 60 else 0)),
        "t_score": min(10, 3 + (3 if any(term in lower for term in ("goal", "task", "needed", "responsible")) else 0)),
        "a_score": min(10, 3 + (3 if " i " in f" {lower} " else 0) + (2 if any(term in lower for term in ("built", "created", "implemented", "led", "debugged")) else 0)),
        "r_score": min(10, 3 + (3 if any(term in lower for term in ("result", "outcome", "improved", "reduced", "increased")) else 0) + (2 if any(char.isdigit() for char in draft) else 0)),
    }


def _fallback_rewrite(question: str, draft: str, weakest: str) -> str:
    if weakest == "s_score":
        return f"In a relevant project related to {question.rstrip('?').lower()}, I started by clarifying the user need, constraints, and success criteria."
    if weakest == "t_score":
        return "My responsibility was to define the next step, prioritize the highest-risk issue, and keep the work aligned with the expected outcome."
    if weakest == "a_score":
        return "I broke the problem into smaller steps, implemented the fix, validated it with testing, and communicated progress clearly."
    return "As a result, the work produced a measurable improvement and gave the team a repeatable approach for similar situations."


def build_star_feedback(question: str, draft: str, category: str = "behavioral") -> dict:
    prompt = f"""
Question: {question}
Draft answer: {draft}

Score each STAR element from 1-10.
Identify the weakest element.
Rewrite only that element as a model improvement.
Return strict JSON with keys:
s_score, t_score, a_score, r_score, weakest_element, rewrite
"""
    llm_text = call_llm(prompt)
    parsed = extract_json_object(llm_text or "")
    scores = _heuristic_star_scores(draft)
    if parsed:
        for key in scores:
            try:
                scores[key] = max(1, min(10, int(parsed.get(key, scores[key]))))
            except (TypeError, ValueError):
                pass
    weakest = min(scores, key=scores.get)
    rewrite = str((parsed or {}).get("rewrite") or _fallback_rewrite(question, draft, weakest))
    result = {
        **scores,
        "weakest_element": str((parsed or {}).get("weakest_element") or weakest.replace("_score", "").upper()),
        "rewrite": rewrite,
        "scorecard": build_answer_scorecard(question, draft),
        "sentence_count": sentence_count(draft),
    }

    saved = read_json(STAR_ANSWERS_PATH, {})
    key = slugify(category)
    saved.setdefault(key, [])
    saved[key].append({"question": question, "draft": draft, "feedback": result})
    write_json(STAR_ANSWERS_PATH, saved)
    return result


@tool("build_star_answer")
def build_star_answer(question: str, draft_answer: str, category: str = "behavioral") -> str:
    """
    Score STAR completeness for an answer, rewrite the weakest STAR element, and save feedback.
    """
    return json.dumps(build_star_feedback(question, draft_answer, category), indent=2)
