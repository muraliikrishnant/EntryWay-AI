import json
import re

from crewai.tools import tool

from tools.interview_utils import ACTION_VERBS, extract_keywords, keyword_hits, words
from tools.resume_tool import read_my_resume


def score_resume_text(resume_text: str, job_description: str) -> dict:
    jd_keywords = extract_keywords(job_description, limit=20)
    matched = keyword_hits(resume_text, jd_keywords)
    missing = [keyword for keyword in jd_keywords if keyword not in matched]
    bullets = [line.strip() for line in resume_text.splitlines() if line.strip().startswith(("-", "*"))]
    if not bullets:
        bullets = [line.strip() for line in resume_text.splitlines() if len(line.strip()) > 35]
    quantified_bullets = [
        bullet for bullet in bullets if re.search(r"\b\d+([.%x]| percent| users| tickets| hours| days| weeks)?\b", bullet)
    ]
    resume_words = words(resume_text)
    active_hits = [word for word in resume_words if word in ACTION_VERBS]
    passive_hits = len(re.findall(r"\b(was|were|been|being|responsible for|helped with)\b", resume_text.lower()))
    sections = {
        "summary": "summary" in resume_text.lower() or "profile" in resume_text.lower(),
        "skills": "skills" in resume_text.lower(),
        "experience": "experience" in resume_text.lower(),
        "education": "education" in resume_text.lower(),
        "projects": "project" in resume_text.lower(),
    }
    missing_sections = [name for name, present in sections.items() if not present]
    match_pct = round((len(matched) / max(1, len(jd_keywords))) * 100)
    quantified_pct = round((len(quantified_bullets) / max(1, len(bullets))) * 100)
    readability = min(100, max(35, 70 + (10 if sections["skills"] else 0) - min(20, passive_hits * 2)))
    credibility = min(100, max(30, 45 + quantified_pct // 2 + min(20, len(active_hits))))

    fixes = []
    if missing:
        fixes.append(f"Add evidence for these job keywords: {', '.join(missing[:5])}.")
    if quantified_pct < 50:
        fixes.append("Rewrite bullets to include measurable scope, frequency, or outcome.")
    if passive_hits > 3:
        fixes.append("Replace passive wording with direct action verbs.")
    if missing_sections:
        fixes.append(f"Add or clarify missing sections: {', '.join(missing_sections[:3])}.")

    return {
        "ats_score": match_pct,
        "readability": readability,
        "credibility": credibility,
        "matched_keywords": matched,
        "missing_keywords": missing[:10],
        "active_voice_hits": len(active_hits),
        "passive_voice_hits": passive_hits,
        "quantified_bullet_percent": quantified_pct,
        "missing_sections": missing_sections,
        "top_3_fixes": fixes[:3],
    }


@tool("score_my_resume")
def score_my_resume(job_description: str, resume_path: str = "") -> str:
    """
    Score the candidate resume against a job description for ATS keyword match and bullet strength.
    """
    resume_text = read_my_resume.run(resume_path)
    return json.dumps(score_resume_text(resume_text, job_description), indent=2)
