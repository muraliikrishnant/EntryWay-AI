import json
import re

from crewai.tools import tool

from tools.interview_utils import (
    ACTION_VERBS,
    CONFIDENCE_WORDS,
    count_filler_words,
    extract_keywords,
    keyword_hits,
    sentence_count,
    words,
)


def build_answer_scorecard(question: str, answer: str, keywords: list[str] | None = None) -> dict:
    answer_words = words(answer)
    word_count = len(answer_words)
    lower = answer.lower()
    keywords = keywords or extract_keywords(question, limit=8)
    matched_keywords = keyword_hits(answer, keywords)
    action_verbs_used = sorted({word for word in answer_words if word in ACTION_VERBS})
    quantified = bool(re.search(r"\b\d+([.%x]| percent| users| tickets| hours| days| weeks)?\b", answer))
    filler_count = count_filler_words(answer)
    confidence_hits = sorted({word for word in answer_words if word in CONFIDENCE_WORDS})

    star_markers = sum(
        1
        for marker_group in (
            ("situation", "context", "when", "while"),
            ("task", "goal", "needed", "responsible"),
            ("action", "i built", "i created", "i led", "i implemented", "i worked"),
            ("result", "outcome", "improved", "reduced", "increased", "learned"),
        )
        if any(marker in lower for marker in marker_group)
    )
    star_score = min(10, max(1, round((star_markers / 4) * 8 + (2 if quantified else 0))))

    relevance = min(
        10,
        max(
            1,
            round(
                3
                + min(4, len(matched_keywords))
                + min(2, len(action_verbs_used))
                + (1 if 80 <= word_count <= 220 else 0)
            ),
        ),
    )
    if word_count < 40:
        top_tip = "Add enough context, action detail, and a measurable result."
    elif not quantified:
        top_tip = "Add a concrete metric or outcome to make the answer more credible."
    elif star_score < 7:
        top_tip = "Make the Situation, Task, Action, and Result structure more explicit."
    elif filler_count:
        top_tip = "Remove filler words and tighten the answer."
    else:
        top_tip = "Tie the result back to the role requirements more directly."

    return {
        "star_score": star_score,
        "filler_word_count": filler_count,
        "keywords_matched": matched_keywords,
        "action_verbs_used": action_verbs_used,
        "has_quantified_result": quantified,
        "word_count": word_count,
        "sentence_count": sentence_count(answer),
        "confidence_vocabulary": confidence_hits,
        "relevance_score": relevance,
        "top_tip": top_tip,
    }


@tool("score_mock_answer")
def score_mock_answer(question: str, answer: str, keywords_csv: str = "") -> str:
    """
    Score an interview answer on STAR structure, filler words, keywords, verbs, length, and relevance.
    """
    keywords = [keyword.strip() for keyword in keywords_csv.split(",") if keyword.strip()]
    return json.dumps(build_answer_scorecard(question, answer, keywords or None), indent=2)
