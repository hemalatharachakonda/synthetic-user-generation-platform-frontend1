import streamlit as st
from utils.state_manager import init_session_state, has_personas
from components.report_preview import report_preview
from services.api_client import extract_insights, generate_report
from services.export_service import build_report_pdf
from styles.theme import load_css

st.set_page_config(page_title="Report Generator", layout="wide")
init_session_state()

css = load_css("styles/custom.css")
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.markdown('<div class="eyebrow">Deliverable</div>', unsafe_allow_html=True)
st.title("Research Report")

if not has_personas():
    st.warning("No personas yet. Create an experiment first.")
    if st.button("Go to Experiment Workspace"):
        st.switch_page("pages/1_Experiment_Workspace.py")
    st.stop()

if st.session_state.insights is None:
    with st.spinner("Extracting insights..."):
        st.session_state.insights = extract_insights(
            st.session_state.personas,
            st.session_state.survey_responses,
            st.session_state.chat_history,
        )

experiment = st.session_state.experiment
personas = st.session_state.personas
insights = st.session_state.insights

report_preview(experiment, personas, insights)

st.divider()
col1, col2 = st.columns(2)

with col1:
    pdf_bytes = build_report_pdf(experiment, personas, insights)
    st.download_button(
        "Download PDF", data=pdf_bytes,
        file_name=f"{experiment['product_name'].replace(' ', '_')}_report.pdf",
        mime="application/pdf", use_container_width=True, type="primary",
    )

with col2:
    if st.button("View Full Dashboard", use_container_width=True):
        st.switch_page("pages/5_Insights_Dashboard.py")

if not st.session_state.report_generated:
    st.session_state.report_generated = True
    st.session_state.report_data = generate_report(experiment, personas, insights)
    history_entry = {**experiment, "would_use_pct": insights.get("would_use_pct")}
    st.session_state.experiments_history.append(history_entry)
