import streamlit as st
from config import APP_NAME, APP_ICON, APP_TAGLINE, GROQ_API_KEY, BACKEND_BASE_URL
from utils.state_manager import init_session_state, has_experiment, reset_experiment_state
from services.api_client import list_recent_experiments, get_experiment, get_personas_for_experiment, delete_experiment
from styles.theme import load_css

st.set_page_config(page_title="Home", page_icon=APP_ICON, layout="wide")
init_session_state()

css = load_css("styles/custom.css")
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

backend_recent = list_recent_experiments() if BACKEND_BASE_URL else []

if BACKEND_BASE_URL and st.session_state.get("_backend_status") == "connected":
    st.caption("Connected to backend — experiments, personas, and interviews persist and resume across sessions.")
elif BACKEND_BASE_URL:
    st.warning(
        f"Backend URL is set but not reachable right now, so this session is running on local/Groq "
        f"data instead (nothing will persist). If he's on Render free tier, the first request after "
        f"idling can take 30-60s to wake up — try reloading in a minute. "
        f"Details: {st.session_state.get('_backend_last_error', 'unknown error')}"
    )
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
    if st.button("Start New Experiment", width='stretch', type="primary"):
        st.switch_page("pages/1_Experiment_Workspace.py")
with c2:
    if st.button("View Dashboard", width='stretch', disabled=not has_experiment()):
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

if backend_recent:
    dismissed = st.session_state.get("dismissed_experiment_ids", set())
    for exp in [e for e in backend_recent if e.get("id") not in dismissed]:
        with st.container(border=True):
            cols = st.columns([3, 1, 1, 1])
            cols[0].markdown(f"**{exp.get('title', 'Untitled experiment')}**")
            label, tier_class = STATUS_LABELS.get(exp.get("status"), ("Unknown", "score-mid"))
            cols[1].markdown(f'<span class="score-badge {tier_class}">{label.upper()}</span>', unsafe_allow_html=True)
            if cols[2].button("Resume", key=f"resume_{exp['id']}", width='stretch'):
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

            confirm_key = f"confirm_delete_{exp['id']}"
            if cols[3].button("Delete", key=f"delete_{exp['id']}", width='stretch'):
                st.session_state[confirm_key] = True
            if st.session_state.get(confirm_key):
                st.warning(f"Permanently delete **{exp.get('title', 'this experiment')}** and all its personas/surveys/interviews?")
                cc1, cc2 = st.columns(2)
                if cc1.button("Yes, delete it", key=f"confirm_yes_{exp['id']}", type="primary"):
                    if delete_experiment(exp["id"]):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                    else:
                        st.error("Couldn't delete — backend unreachable. Try again in a moment.")
                if cc2.button("Cancel", key=f"confirm_no_{exp['id']}"):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
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
                if cols[2].button("Delete", key=f"delete_{exp.get('id', exp['product_name'])}", width='stretch'):
                    st.session_state.dismissed_experiment_ids.add(exp.get("id", exp["product_name"]))
                    st.rerun()
