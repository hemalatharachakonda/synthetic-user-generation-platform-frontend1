"""
Central configuration for the Synthetic User Generation Platform frontend.

IMPORTANT — SWAPPING FROM MOCK DATA TO YOUR REAL BACKEND:
1. Set USE_MOCK_DATA = False (or the Streamlit secret) to use the real backend
   for Experiments + Persona generation. Survey, Interview, and Insights run on
   Groq directly (when GROQ_API_KEY is set) regardless of this flag, since
   those endpoints aren't built on the backend yet.
2. Set BACKEND_BASE_URL to the deployed backend, including its /api/v1 prefix,
   e.g. "https://synthetic-user-generation-platform-2.onrender.com/api/v1".
3. Set GROQ_API_KEY for real Survey/Interview/Insights responses.
Everything else in the app calls services/api_client.py, which already branches
on USE_MOCK_DATA / GROQ_API_KEY, so no other files need to change.
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


# ── Mode toggle ──────────────────────────────────────────────────────────────
USE_MOCK_DATA = _get_setting("USE_MOCK_DATA", "true").lower() == "true"

# ── Backend ──────────────────────────────────────────────────────────────────
BACKEND_BASE_URL = _get_setting("BACKEND_BASE_URL", "http://localhost:8000/api")
API_TIMEOUT_SECONDS = 30

# ── Groq (only used if frontend calls the LLM directly; optional) ───────────
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
