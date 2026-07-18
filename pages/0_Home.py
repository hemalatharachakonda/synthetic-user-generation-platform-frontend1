import streamlit as st
from config import APP_NAME, APP_ICON, APP_TAGLINE, GROQ_API_KEY, BACKEND_BASE_URL
from utils.state_manager import init_session_state, has_experiment, reset_experiment_state
from services.api_client import list_recent_experiments, get_experiment, get_personas_for_experiment
from styles.theme import load_css

st.set_page_config(page_title="Home", page_icon=APP_ICON, layout="wide")
init_session_state()

css = load_css("styles/custom.css")
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

if BACKEND_BASE_URL:
    st.caption("Connected to backend — experiments, personas, and interviews persist and resume across sessions.")
elif GROQ_API_KEY:
    st.caption("Personas, surveys, interviews, and insights are generated live by Groq AI. No backend configured — nothing persists across sessions.")
else:
    st.caption("No backend or Groq API key configured — running on local sample data only.")

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

STATUS_LABELS = {
    "draft": ("Not started", "score-low"),
    "personas_ready": ("Personas ready", "score-mid"),
    "running": ("In progress", "score-mid"),
    "completed": ("Completed", "score-high"),
    "archived": ("Archived", "score-low"),
}

backend_recent = list_recent_experiments() if BACKEND_BASE_URL else []

if backend_recent:
    dismissed = st.session_state.get("dismissed_experiment_ids", set())
    for exp in [e for e in backend_recent if e.get("id") not in dismissed]:
        with st.container(border=True):
            cols = st.columns([3, 1, 1])
            cols[0].markdown(f"**{exp.get('title', 'Untitled experiment')}**")
            label, tier_class = STATUS_LABELS.get(exp.get("status"), ("Unknown", "score-mid"))
            cols[1].markdown(f'<span class="score-badge {tier_class}">{label.upper()}</span>', unsafe_allow_html=True)
            if cols[2].button("Resume", key=f"resume_{exp['id']}", use_container_width=True):
                reset_experiment_state()
                loaded = get_experiment(exp["id"])
                if loaded:
                    st.session_state.experiment = loaded
                    st.session_state.personas = get_personas_for_experiment(exp["id"])
                    # Route to wherever makes sense for how far this experiment got.
                    if exp.get("status") in ("completed",):
                        st.switch_page("pages/5_Insights_Dashboard.py")
                    elif st.session_state.personas:
                        st.switch_page("pages/2_Persona_Gallery.py")
                    else:
                        st.switch_page("pages/1_Experiment_Workspace.py")
                else:
                    st.error("Couldn't load that experiment — it may have been deleted.")
else:
    # No backend configured (or nothing reachable) — fall back to the
    # session-local history of completed runs, as before.
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
