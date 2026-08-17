import streamlit as st
from config import APP_NAME, APP_ICON, APP_TAGLINE, GROQ_API_KEY
from utils.state_manager import init_session_state, has_experiment
from services.api_client import list_backend_experiments, resume_backend_experiment
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
    if st.button("Start New Experiment", width='stretch', type="primary"):
        st.switch_page("pages/1_Experiment_Workspace.py")
with c2:
    if st.button("View Dashboard", width='stretch', disabled=not has_experiment()):
        st.switch_page("pages/5_Insights_Dashboard.py")
    if not has_experiment():
        st.caption("Create an experiment first to unlock the dashboard.")

st.markdown('<div class="section-label">Recent Experiments</div>', unsafe_allow_html=True)

# The backend is the real source of truth (survives reloads); session-only
# history is used only as a fallback for entries the backend doesn't know
# about yet (e.g. backend was unreachable when this ran).
if "recent_experiments_loaded" not in st.session_state:
    with st.spinner("Loading recent experiments..."):
        backend_recent = list_backend_experiments()
    if backend_recent is not None:
        backend_ids = {e["id"] for e in backend_recent}
        session_only = [
            e for e in st.session_state.get("experiments_history", [])
            if e.get("id") not in backend_ids
        ]
        st.session_state.experiments_history = backend_recent + session_only
    st.session_state.recent_experiments_loaded = True

dismissed = st.session_state.get("dismissed_experiment_ids", set())
recent = [e for e in st.session_state.get("experiments_history", []) if e.get("id") not in dismissed]

if not recent:
    st.info("No experiments logged yet. Start your first one above!")
else:
    for exp in recent[:5]:
        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1])
            cols[0].markdown(f"**{exp['product_name']}**")
            pct = exp.get("would_use_pct", 0)
            tier_color = "score-high" if pct >= 60 else "score-mid" if pct >= 40 else "score-low"
            cols[1].markdown(
                f'<span class="score-badge {tier_color}">{pct}% WOULD USE</span>',
                unsafe_allow_html=True,
            )
            if exp.get("_backend"):
                if cols[2].button("Resume", key=f"resume_{exp['id']}", width='stretch'):
                    with st.spinner("Loading experiment..."):
                        result = resume_backend_experiment(exp["id"])
                    if result:
                        st.session_state.experiment, st.session_state.personas = result
                        st.switch_page("pages/5_Insights_Dashboard.py")
                    else:
                        st.error("Couldn't load this experiment from the backend right now.")
            if cols[3].button("Delete", key=f"delete_{exp.get('id', exp['product_name'])}", width='stretch'):
                st.session_state.dismissed_experiment_ids.add(exp.get("id", exp["product_name"]))
                st.rerun()
