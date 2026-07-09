"""
Central configuration for the Synthetic User Generation Platform frontend.

This app runs entirely without a backend server. Experiments and Personas are
generated locally: names/ages/occupations come from local mock pools, while
personality traits, adoption scores, bios, and quotes are generated live by
Groq (when GROQ_API_KEY is set). Survey, Interview, and Insights work the
same way. Set GROQ_API_KEY below (or as a Streamlit secret) to enable real
AI-generated responses everywhere; without it, everything falls back to
local sample data automatically, so the app always works either way.
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

# ── Groq — powers Persona/Survey/Interview/Insights generation ─────────────
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
