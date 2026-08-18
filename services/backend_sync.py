"""
Best-effort sync to the backend database.

The rest of the app (Groq/local generation in api_client.py) is the source
of truth for what's on screen and never depends on this succeeding — it
behaves exactly as if there were no backend at all. This module's only job
is to also save a copy of what was created (experiment, personas, ...) to
the backend database, without ever showing the user an error or breaking
the page if the backend is slow/unreachable.

- sync_experiment(): saves the experiment and returns the backend's own id
  for it (needed so personas can be linked to the right row), bounded by a
  short timeout so it can't hang the page — on any failure it just returns
  None and the rest of the app carries on exactly as before.
- sync_personas(): fires in a background thread and returns immediately;
  nothing waits on it, so it truly can't slow anything down.
"""

import threading
import requests

from config import BACKEND_URL, BACKEND_API_PREFIX

API_BASE = f"{BACKEND_URL}{BACKEND_API_PREFIX}"
SYNC_TIMEOUT_SECONDS = 5


def sync_experiment(experiment: dict) -> str | None:
    """Saves the experiment to the backend database. Returns the backend's
    id for it, or None if the backend was slow/unreachable/errored — never
    raises, so callers can always safely ignore the return value."""
    payload = {
        "title": experiment.get("product_name", ""),
        "product_description": experiment.get("description", ""),
        "target_audience": experiment.get("target_audience", ""),
        "research_objectives": experiment.get("objectives", ""),
        "persona_count": experiment.get("persona_count", 6),
    }
    try:
        resp = requests.post(f"{API_BASE}/experiments", json=payload, timeout=SYNC_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.json().get("id")
    except requests.RequestException:
        return None


def _post_personas(experiment_id: str, personas: list[dict]) -> None:
    payload = {
        "experiment_id": experiment_id,
        "replace": True,
        "personas": [
            {
                "name": p.get("name", ""),
                "age": p.get("age"),
                "occupation": p.get("occupation"),
                "location": p.get("location"),
                "tags": p.get("tags", []),
                "behavioral_pattern": p.get("behavioral_pattern"),
                "bio": p.get("bio", ""),
                "avatar_seed": p.get("avatar_seed"),
                "quote": p.get("quote"),
                "adoption_score": p.get("adoption_score"),
            }
            for p in personas
        ],
    }
    try:
        requests.post(f"{API_BASE}/personas/import", json=payload, timeout=SYNC_TIMEOUT_SECONDS)
    except requests.RequestException:
        pass  # offline/unreachable backend must never affect the running app


def sync_personas(experiment_id: str | None, personas: list[dict]) -> None:
    """Saves the exact personas already shown in the UI (same names, ages,
    occupations, bios, tags, adoption scores) to the backend database, in a
    background thread — the caller never waits on this."""
    if not experiment_id or not personas:
        return
    threading.Thread(target=_post_personas, args=(experiment_id, personas), daemon=True).start()
