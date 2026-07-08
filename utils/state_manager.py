"""
Centralized session_state initialization and helpers.
Import init_session_state() at the top of every page so state is always safe to read.
"""

import uuid
import streamlit as st


def init_session_state():
    defaults = {
        "user_id": f"user_{uuid.uuid4().hex[:8]}",
        "session_id": f"sess_{uuid.uuid4().hex[:8]}",

        "experiment": None,           # dict once created
        "experiments_history": [],    # list of past experiment summaries

        "personas": [],                # list of persona dicts
        "current_interview": None,     # persona id currently being interviewed
        "chat_history": {},            # {persona_id: [ {role, content}, ... ]}

        "current_question_index": 0,
        "survey_questions": [],        # list of question strings
        "survey_responses": {},        # {question_index: {persona_id: {"score":.., "comment":..}}}

        "theme": "light",
        "expanded_sections": [],

        "insights": None,
        "insights_fingerprint": None,  # tracks what data insights were computed from, to auto-refresh when it changes
        "report_generated": False,
        "report_data": None,

        "dismissed_experiment_ids": set(),  # frontend-only "delete" — hides from Recent Experiments, never touches the backend DB
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_experiment_state():
    """Clears everything tied to a single experiment run (personas, chats, survey, insights)."""
    st.session_state.experiment = None
    st.session_state.personas = []
    st.session_state.current_interview = None
    st.session_state.chat_history = {}
    st.session_state.current_question_index = 0
    st.session_state.survey_questions = []
    st.session_state.survey_responses = {}
    st.session_state.insights = None
    st.session_state.report_generated = False
    st.session_state.report_data = None


def get_persona_by_id(persona_id: str):
    for p in st.session_state.get("personas", []):
        if p["id"] == persona_id:
            return p
    return None


def has_experiment() -> bool:
    return st.session_state.get("experiment") is not None


def has_personas() -> bool:
    return len(st.session_state.get("personas", [])) > 0
