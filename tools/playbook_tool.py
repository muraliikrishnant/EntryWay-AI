import json
import os
from pathlib import Path

from crewai.tools import tool

from tools.interview_utils import read_json

PLAYBOOK_DIR = Path("config/playbooks")


def load_candidate_playbook(candidate_type: str | None = None) -> dict:
    selected = candidate_type or os.getenv("CANDIDATE_TYPE", "perm_resident")
    path = PLAYBOOK_DIR / f"{selected}.json"
    if not path.exists():
        path = PLAYBOOK_DIR / "perm_resident.json"
    return read_json(path, {})


@tool("get_candidate_playbook")
def get_candidate_playbook(candidate_type: str = "") -> str:
    """
    Load candidate-track guidance for cover letters, matching, and interview prep.
    """
    return json.dumps(load_candidate_playbook(candidate_type or None), indent=2)
