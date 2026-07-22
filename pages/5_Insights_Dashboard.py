import streamlit as st
from utils.state_manager import init_session_state, has_personas, get_persona_by_id
from components.visualizations import adoption_chart, sentiment_donut, theme_bars
from components.suggestions_panel import render_user_wants_summary, render_suggestions
from components.persona_card import persona_card
from services.api_client import extract_insights
from styles.theme import load_css

st.set_page_config(page_title="Insights Dashboard", layout="wide")
init_session_state()

css = load_css("styles/custom.css")
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.markdown('<div class="eyebrow">Findings</div>', unsafe_allow_html=True)
st.title("Experiment Dashboard")

if not has_personas():
    st.warning("No personas yet. Create an experiment first.")
    if st.button("Go to Experiment Workspace"):
        st.switch_page("pages/1_Experiment_Workspace.py")
    st.stop()

experiment = st.session_state.experiment
st.markdown(
    f'<h3 style="margin-top:-0.4rem; color: var(--accent);">{experiment["product_name"]}</h3>',
    unsafe_allow_html=True,
)

tab_overview, tab_personas, tab_survey, tab_interviews, tab_insights = st.tabs(
    ["Overview", "Personas", "Survey Responses", "Interviews", "Insights"]
)

# ── Overview ──────────────────────────────────────────────────────────────────
with tab_overview:
    STATUS_LABELS = {
        "draft": "Not started", "personas_ready": "Personas ready",
        "running": "In progress", "completed": "Completed", "archived": "Archived",
    }
    st.markdown('<div class="section-label">Experiment Details</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown(
            f'<div style="background: var(--surface); border-radius: 10px; padding: 0.5rem 0.75rem;">'
            f'<p style="color: var(--ink);"><b>Product:</b> {experiment.get("product_name", "")}</p>'
            f'<p style="color: var(--ink);"><b>Description:</b> {experiment.get("description", "")}</p>'
            f'<p style="color: var(--ink);"><b>Target audience:</b> {experiment.get("target_audience", "")}</p>'
            f'<p style="color: var(--ink);"><b>Research objectives:</b> {experiment.get("objectives", "")}</p>'
            f'<p style="color: var(--ink);"><b>Status:</b> {STATUS_LABELS.get(experiment.get("status"), experiment.get("status", "unknown"))}</p>'
            f'<p style="color: var(--ink);"><b>Personas:</b> {len(st.session_state.personas)} generated</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Personas ──────────────────────────────────────────────────────────────────
with tab_personas:
    st.markdown('<div class="section-label">Panel Roster</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    for i, p in enumerate(st.session_state.personas):
        with cols[i % 2]:
            def _go_interview(pid):
                st.session_state.current_interview = pid
                st.switch_page("pages/4_Interview_Mode.py")
            persona_card(p, on_interview=_go_interview)

# ── Survey Responses ──────────────────────────────────────────────────────────
with tab_survey:
    st.markdown('<div class="section-label">Every Question Asked</div>', unsafe_allow_html=True)
    survey_rows = []
    # Local/session-only — build the same shape from session state.
    for q_idx, q_text in enumerate(st.session_state.survey_questions):
        for p in st.session_state.personas:
            r = (st.session_state.survey_responses.get(q_idx) or {}).get(p["id"])
            if r:
                survey_rows.append({
                    "question": q_text, "persona_id": p["id"], "persona_name": p["name"],
                    "answer": r.get("comment", ""), "rating": r.get("score"),
                })

    if not survey_rows:
        st.info("No survey questions asked yet.")
    else:
        by_question = {}
        for row in survey_rows:
            by_question.setdefault(row["question"], []).append(row)
        for question, rows in by_question.items():
            st.markdown(f"#### \u201c{question}\u201d")
            for row in rows:
                with st.container(border=True):
                    st.markdown(
                        f'<div style="background: var(--surface); border-radius: 10px; padding: 0.5rem 0.75rem;">'
                        f'<span class="score-badge score-mid">{row.get("rating", "-")}/10</span> '
                        f'<span style="color: var(--ink); font-weight: 700;">{row["persona_name"]}</span>'
                        f'<div style="color: var(--ink); font-style: italic; margin-top: 0.3rem;">\u201c{row["answer"]}\u201d</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

# ── Interviews ────────────────────────────────────────────────────────────────
with tab_interviews:
    st.markdown('<div class="section-label">Every Interview Transcript</div>', unsafe_allow_html=True)
    transcripts = {}
    for pid, turns in st.session_state.chat_history.items():
        if turns:
            transcripts[pid] = turns

    if not transcripts:
        st.info("No interviews conducted yet.")
    else:
        for pid, turns in transcripts.items():
            persona = get_persona_by_id(pid)
            label = persona["name"] if persona else pid
            with st.expander(f"{label} — {len(turns)} messages"):
                for turn in turns:
                    role = "You" if turn.get("role") == "user" else label
                    st.markdown(f"**{role}:** {turn.get('content', '')}")

# ── Insights (charts + suggestions) ────────────────────────────────────────────
with tab_insights:
    def _current_data_fingerprint() -> tuple:
        """A cheap signature of the data insights would be based on. If this
        changes (new interview turns, new survey answers, different personas),
        the cached insights are stale and should be recalculated automatically."""
        persona_ids = tuple(sorted(p["id"] for p in st.session_state.personas))
        chat_turns = sum(len(turns) for turns in st.session_state.chat_history.values())
        survey_answers = sum(len(r) for r in st.session_state.survey_responses.values())
        return (persona_ids, chat_turns, survey_answers)

    current_fingerprint = _current_data_fingerprint()
    needs_recalc = (
        st.session_state.insights is None
        or st.session_state.insights_fingerprint != current_fingerprint
    )

    if st.button("Recalculate Insights") or needs_recalc:
        with st.spinner("Extracting insights..."):
            st.session_state.insights = extract_insights(
                st.session_state.personas,
                st.session_state.survey_responses,
                st.session_state.chat_history,
            )
            st.session_state.insights_fingerprint = current_fingerprint

    insights = st.session_state.insights

    # ── Headline metrics — clear at-a-glance readout ─────────────────────────
    st.markdown(
        f"""
        <div class="insight-metric-row">
            <div class="insight-metric-card">
                <div class="im-label">Would Use</div>
                <div class="im-value">{insights.get('would_use_pct', 'N/A')}%</div>
                <div class="im-sub">of simulated target users</div>
            </div>
            <div class="insight-metric-card">
                <div class="im-label">Would Pay</div>
                <div class="im-value">{insights.get('would_pay_pct', 'N/A')}%</div>
                <div class="im-sub">willing to pay for it</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── What users want — plain-English summary, grounded in real feedback ──
    render_user_wants_summary(insights.get("user_wants_summary", ""))

    st.markdown('<div class="section-label">Theme Clusters & Sentiment</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        theme_bars(insights["themes"])
    with c2:
        sentiment_donut(insights["sentiment"])

    st.markdown('<div class="section-label">Suggestions To Improve The Product</div>', unsafe_allow_html=True)
    st.caption("Ranked by priority — grounded in what personas actually said in interviews and surveys.")
    render_suggestions(insights.get("suggestions", []))

    st.markdown('<div class="section-label">Adoption by Persona</div>', unsafe_allow_html=True)
    adoption_chart(st.session_state.personas)

    st.markdown('<div class="section-label">Key Quotes</div>', unsafe_allow_html=True)
    quote_cards = []
    for q in insights.get("key_quotes", []):
        # Compact single-line HTML — indented multi-line f-strings get treated
        # by Streamlit's markdown renderer as a Markdown code block (4+ leading
        # spaces), which silently breaks rendering after the first item.
        quote_cards.append(
            '<div class="quote-card-clean">'
            '<span class="qmark">\u201c</span>'
            f'<div class="qtext">{q["quote"]}</div>'
            f'<div class="qmeta">— {q["persona"]}</div>'
            '</div>'
        )
    if quote_cards:
        st.markdown(f'<div class="quote-grid">{"".join(quote_cards)}</div>', unsafe_allow_html=True)
    else:
        st.info("No quotes yet.")

    st.divider()
    if st.button("Generate Full Report", type="primary"):
        st.switch_page("pages/6_Report_Generator.py")
