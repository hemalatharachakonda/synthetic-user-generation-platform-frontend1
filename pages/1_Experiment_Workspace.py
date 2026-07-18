import streamlit as st
from config import DEFAULT_PERSONA_COUNT, MIN_PERSONA_COUNT, MAX_PERSONA_COUNT
from utils.state_manager import init_session_state, reset_experiment_state
from utils.validators import validate_experiment_form
from services.api_client import create_experiment, generate_personas
from styles.theme import load_css

st.set_page_config(page_title="Experiment Workspace", layout="wide")
init_session_state()

css = load_css("styles/custom.css")
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.markdown('<div class="eyebrow">New Study</div>', unsafe_allow_html=True)
st.title("Create New Experiment")

with st.form("experiment_form"):
    st.markdown('<div class="step-marker"><span class="num">1</span> Define Your Product</div>', unsafe_allow_html=True)
    product_name = st.text_input("Product Name", placeholder="e.g. FitTrack Pro", label_visibility="collapsed")
    description = st.text_area(
        "Description",
        placeholder="AI-powered fitness app for busy professionals with personalized...",
        height=100, label_visibility="collapsed",
    )

    st.markdown('<div class="step-marker"><span class="num">2</span> Target Audience</div>', unsafe_allow_html=True)
    target_audience = st.text_area(
        "Target Audience",
        placeholder="Urban professionals, ages 25-40, tech-savvy, health-conscious...",
        height=80, label_visibility="collapsed",
    )

    st.markdown('<div class="step-marker"><span class="num">3</span> Research Objectives</div>', unsafe_allow_html=True)
    objectives = st.text_area(
        "Research Objectives",
        placeholder="Understand fitness tracking habits, identify desired features, test pricing...",
        height=80, label_visibility="collapsed",
    )

    persona_count = st.slider(
        "Number of Personas", min_value=MIN_PERSONA_COUNT,
        max_value=MAX_PERSONA_COUNT, value=DEFAULT_PERSONA_COUNT,
    )

    submitted = st.form_submit_button("Generate Personas", type="primary", width='stretch')

if submitted:
    errors = validate_experiment_form(product_name, description, target_audience, objectives)
    if errors:
        for e in errors:
            st.error(e)
    else:
        reset_experiment_state()
        with st.spinner("Creating experiment..."):
            experiment = create_experiment(product_name, description, target_audience, objectives, persona_count)
            st.session_state.experiment = experiment

        with st.spinner(f"Generating {persona_count} personas..."):
            personas = generate_personas(st.session_state.experiment, product_name, description, target_audience, objectives, persona_count)
            st.session_state.personas = personas
            if not st.session_state.experiment.get("_backend"):
                st.session_state.experiment["status"] = "personas_generated"

        st.success(f"Generated {len(personas)} personas!")
        st.switch_page("pages/2_Persona_Gallery.py")

if st.session_state.get("experiment"):
    st.divider()
    if st.button("⏳ Load Existing Experiment Personas"):
        st.switch_page("pages/2_Persona_Gallery.py")
