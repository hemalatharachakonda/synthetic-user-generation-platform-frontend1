import streamlit as st
from config import APP_NAME, APP_ICON, APP_TAGLINE, GROQ_API_KEY
from utils.state_manager import init_session_state, has_experiment
from styles.theme import load_css

st.set_page_config(page_title="Home", page_icon=APP_ICON, layout="wide")
init_session_state()

css = load_css("styles/custom.css")
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

if GROQ_API_KEY:
    st.caption("Personas, surveys, interviews, and insights are generated live by Groq AI.")
else:
    st.caption("No Groq API key configured — running on local sample data only.")

st.markdown(
    f"""
    <div class="lab-hero">
        <div class="eyebrow">Field Log — Synthetic Research Unit</div>
        <h1>{APP_NAME}</h1>
        <p class="tagline">{APP_TAGLINE}. Recruit a panel of AI-simulated
        subjects in minutes, run the same study you'd run on real users, and
        walk away with a defensible report.</p>
        <div class="readout-row">
            <div class="readout"><span class="val">500+</span><span class="lbl">Personas Logged</span></div>
            <div class="readout"><span class="val">98%</span><span class="lbl">Accuracy Rate</span></div>
            <div class="readout"><span class="val">15 min</span><span class="lbl">Per Test Cycle</span></div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2 = st.columns(2)
with c1:
    if st.button("Start New Experiment", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Experiment_Workspace.py")
with c2:
    if st.button("View Dashboard", use_container_width=True, disabled=not has_experiment()):
        st.switch_page("pages/5_Insights_Dashboard.py")
    if not has_experiment():
        st.caption("Create an experiment first to unlock the dashboard.")

st.markdown('<div class="section-label">Recent Experiments</div>', unsafe_allow_html=True)

dismissed = st.session_state.get("dismissed_experiment_ids", set())
recent = [e for e in st.session_state.get("experiments_history", []) if e.get("id") not in dismissed]

if not recent:
    st.info("No experiments logged yet. Start your first one above!")
else:
    for exp in recent[-5:][::-1]:
        with st.container(border=True):
            cols = st.columns([3, 1, 1])
            cols[0].markdown(f"**{exp['product_name']}**")
            pct = exp.get("would_use_pct", 0)
            tier_color = "score-high" if pct >= 60 else "score-mid" if pct >= 40 else "score-low"
            cols[1].markdown(
                f'<span class="score-badge {tier_color}">{pct}% WOULD USE</span>',
                unsafe_allow_html=True,
            )
            if cols[2].button("Delete", key=f"delete_{exp.get('id', exp['product_name'])}", use_container_width=True):
                st.session_state.dismissed_experiment_ids.add(exp.get("id", exp["product_name"]))
                st.rerun()
