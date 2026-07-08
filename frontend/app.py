import streamlit as st
from config import APP_NAME, APP_ICON
from utils.state_manager import init_session_state
from styles.theme import load_css

st.set_page_config(
    page_title=APP_NAME,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session_state()

css = load_css("styles/custom.css")
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.sidebar.markdown(
    """
    <div style="padding: 0.4rem 0 1rem 0;">
        <div class="eyebrow">Field Research Lab</div>
        <div style="font-family: var(--font-display); font-size: 1.4rem;
                    font-weight: 600; margin-top: 0.2rem;">
            Synthetic Users
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.sidebar.caption("Validate products without real users")
st.sidebar.divider()
st.sidebar.markdown(
    """
    <div style="font-family: var(--font-mono); font-size: 0.78rem; line-height: 1.9;">
    <b>01</b>&nbsp; Experiment Workspace<br>
    <b>02</b>&nbsp; Persona Gallery<br>
    <b>03</b>&nbsp; Survey Mode<br>
    <b>04</b>&nbsp; Interview Mode<br>
    <b>05</b>&nbsp; Insights Dashboard<br>
    <b>06</b>&nbsp; Report Generator
    </div>
    """,
    unsafe_allow_html=True,
)

st.switch_page("pages/0_Home.py")
