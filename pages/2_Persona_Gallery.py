import streamlit as st
from utils.state_manager import init_session_state, has_personas
from components.persona_card import persona_card
from styles.theme import load_css

st.set_page_config(page_title="Persona Gallery", layout="wide")
init_session_state()

css = load_css("styles/custom.css")
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.markdown('<div class="eyebrow">Panel Roster</div>', unsafe_allow_html=True)
st.title("Generated Personas")

if not has_personas():
    st.warning("No personas yet. Create an experiment first.")
    if st.button("Go to Experiment Workspace"):
        st.switch_page("pages/1_Experiment_Workspace.py")
    st.stop()

personas = st.session_state.personas
st.caption(f"{len(personas)} personas generated for **{st.session_state.experiment['product_name']}**")

col_f1, col_f2 = st.columns(2)
with col_f1:
    tag_filter = st.selectbox(
        "Filter by tag",
        options=["All"] + sorted({t for p in personas for t in p.get("tags", [])}),
    )
with col_f2:
    min_score = st.slider("Minimum adoption score", 0.0, 10.0, 0.0, 0.5)

filtered = [
    p for p in personas
    if (tag_filter == "All" or tag_filter in p.get("tags", []))
    and p["adoption_score"] >= min_score
]

st.markdown('<div class="section-label">Specimens</div>', unsafe_allow_html=True)

cols = st.columns(3)


def go_to_interview(persona_id):
    st.session_state.current_interview = persona_id
    st.switch_page("pages/4_Interview_Mode.py")


for i, persona in enumerate(filtered):
    with cols[i % 3]:
        persona_card(persona, on_interview=go_to_interview)

if not filtered:
    st.info("No personas match the current filters.")

st.divider()
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("▶ Run Survey", width='stretch', type="primary"):
        st.switch_page("pages/3_Survey_Mode.py")
with c2:
    if st.button("▶ Start Interviews", width='stretch'):
        st.switch_page("pages/4_Interview_Mode.py")
with c3:
    if st.button("Analyze", width='stretch'):
        st.switch_page("pages/5_Insights_Dashboard.py")
