import streamlit as st
from utils.state_manager import init_session_state, has_personas
from components.visualizations import adoption_chart, sentiment_donut, theme_bars
from components.suggestions_panel import render_user_wants_summary, render_suggestions
from services.api_client import extract_insights
from styles.theme import load_css

st.set_page_config(page_title="Insights Dashboard", layout="wide")
init_session_state()

css = load_css("styles/custom.css")
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.markdown('<div class="eyebrow">Findings</div>', unsafe_allow_html=True)
st.title("Insights Dashboard")

if not has_personas():
    st.warning("No personas yet. Create an experiment first.")
    if st.button("Go to Experiment Workspace"):
        st.switch_page("pages/1_Experiment_Workspace.py")
    st.stop()

st.caption(f"Experiment: **{st.session_state.experiment['product_name']}**")

if st.button("Recalculate Insights") or st.session_state.insights is None:
    with st.spinner("Extracting insights..."):
        st.session_state.insights = extract_insights(
            st.session_state.personas,
            st.session_state.survey_responses,
            st.session_state.chat_history,
        )

insights = st.session_state.insights

# ── Headline metrics — clear at-a-glance readout ─────────────────────────────
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

# ── What users want — plain-English summary, grounded in real feedback ──────
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
