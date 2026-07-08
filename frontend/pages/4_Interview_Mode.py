import streamlit as st
from utils.state_manager import init_session_state, has_personas, get_persona_by_id
from components.chat_interface import chat_interface
from styles.theme import load_css, score_tier

st.set_page_config(page_title="Interview Mode", layout="wide")
init_session_state()

css = load_css("styles/custom.css")
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.markdown('<div class="eyebrow">One-on-One Session</div>', unsafe_allow_html=True)
st.title("Interview Mode")

if not has_personas():
    st.warning("No personas yet. Create an experiment first.")
    if st.button("Go to Experiment Workspace"):
        st.switch_page("pages/1_Experiment_Workspace.py")
    st.stop()

personas = st.session_state.personas

if not st.session_state.current_interview:
    st.session_state.current_interview = personas[0]["id"]

selected_id = st.selectbox(
    "Choose a persona to interview",
    options=[p["id"] for p in personas],
    format_func=lambda pid: get_persona_by_id(pid)["name"],
    index=[p["id"] for p in personas].index(st.session_state.current_interview),
)
st.session_state.current_interview = selected_id
persona = get_persona_by_id(selected_id)
tier = score_tier(persona["adoption_score"])
tier_class = {"high": "score-high", "mid": "score-mid", "low": "score-low"}[tier]

st.subheader(f"Interview: {persona['name']}")
st.markdown(
    f"""
    <div class="specimen-meta">{persona['age']}, {persona['occupation']}
    &nbsp;·&nbsp; <span class="score-badge {tier_class}">{persona['adoption_score']}/10</span></div>
    <div class="specimen-meta">{', '.join(persona.get('tags', []))}</div>
    """,
    unsafe_allow_html=True,
)

st.divider()
chat_interface(persona)

st.divider()
col1, col2 = st.columns(2)
with col1:
    if st.button("End Interview"):
        st.switch_page("pages/2_Persona_Gallery.py")
with col2:
    if st.button("View All Interviews / Insights"):
        st.switch_page("pages/5_Insights_Dashboard.py")
