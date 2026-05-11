import json
import os
import re
from pathlib import Path
from typing import Any

from llm_config import get_llm


ACTION_VERBS = {
    "built",
    "created",
    "designed",
    "developed",
    "implemented",
    "improved",
    "led",
    "optimized",
    "reduced",
    "resolved",
    "shipped",
    "automated",
    "analyzed",
    "debugged",
    "secured",
    "configured",
    "deployed",
    "documented",
}
FILLER_WORDS = {"um", "uh", "like", "so", "basically", "actually", "kind of", "sort of"}
CONFIDENCE_WORDS = {
    "delivered",
    "owned",
    "led",
    "improved",
    "resolved",
    "measured",
    "validated",
    "prioritized",
    "collaborated",
    "recommended",
}


def slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return text.strip("_") or "item"


def read_json(path: str | Path, default: Any) -> Any:
    file_path = Path(path)
    if not file_path.exists():
        return default
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: str | Path, value: Any) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(value, file, indent=2)
        file.write("\n")


def extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def call_llm(prompt: str, *, temperature: float = 0.2) -> str | None:
    """
    Best-effort direct LLM call for CLI tools.
    CrewAI uses the same model config, but these tools should still work without it.
    """
    if os.getenv("DISABLE_DIRECT_LLM", "").lower() in {"1", "true", "yes"}:
        return None
    try:
        from litellm import completion

        response = completion(
            model=get_llm(),
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.choices[0].message.content
    except Exception:
        return None


def words(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9'+-]*", text.lower())


def count_filler_words(text: str) -> int:
    lower = f" {text.lower()} "
    total = 0
    for filler in FILLER_WORDS:
        if " " in filler:
            total += lower.count(f" {filler} ")
        else:
            total += len(re.findall(rf"\b{re.escape(filler)}\b", lower))
    return total


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [kw for kw in keywords if kw and kw.lower() in lower]


def extract_keywords(text: str, limit: int = 10) -> list[str]:
    stop_words = {
        "about",
        "after",
        "also",
        "and",
        "are",
        "for",
        "from",
        "have",
        "into",
        "our",
        "that",
        "the",
        "this",
        "with",
        "you",
        "your",
        "will",
        "work",
        "role",
        "job",
        "team",
        "experience",
    }
    counts: dict[str, int] = {}
    for word in words(text):
        if len(word) < 4 or word in stop_words:
            continue
        counts[word] = counts.get(word, 0) + 1
    return [
        word
        for word, _count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def sentence_count(text: str) -> int:
    return max(1, len([part for part in re.split(r"[.!?]+", text) if part.strip()]))
