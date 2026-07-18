"""
Central configuration for the Synthetic User Generation Platform frontend.

If BACKEND_BASE_URL is set, Experiments/Personas/Survey/Interview/Insights
persist to the real backend (database-backed, resumable across sessions,
with server-side persona memory). If it's unset, or any backend call fails,
everything falls back automatically to Groq direct + local sample data (the
previous fully-local behavior), so the app always works either way.
"""

import os
from dotenv import load_dotenv

load_dotenv()

try:
    import streamlit as st
    _SECRETS = dict(st.secrets) if hasattr(st, "secrets") else {}
except Exception:
    _SECRETS = {}


def _get_setting(key: str, default: str = "") -> str:
    """Check Streamlit Cloud secrets first, then fall back to local .env / OS env.

    This lets the same code work both locally (.env file) and on Streamlit
    Community Cloud (Settings -> Secrets), with no code changes needed.
    """
    if key in _SECRETS:
        return str(_SECRETS[key])
    return os.getenv(key, default)


GROQ_TIMEOUT_SECONDS = 30

# ── Backend — optional. When set, enables persistence + real cross-session
# persona memory. Leave blank to run fully local (Groq direct + mock data). ──
BACKEND_BASE_URL = _get_setting("BACKEND_BASE_URL", "").rstrip("/")
BACKEND_TIMEOUT_SECONDS = 30

# ── Groq — powers Persona/Survey/Interview/Insights generation when no
# backend is configured (or as a fallback if a backend call fails) ─────────
GROQ_API_KEY = _get_setting("GROQ_API_KEY", "")
GROQ_MODEL = _get_setting("GROQ_MODEL", "openai/gpt-oss-120b")

# ── App metadata ─────────────────────────────────────────────────────────────
APP_NAME = "Synthetic User Generation Platform"
APP_ICON = "SU"
APP_TAGLINE = "Validate products without real users"

# ── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_PERSONA_COUNT = 5
MIN_PERSONA_COUNT = 3
MAX_PERSONA_COUNT = 12
