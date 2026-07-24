import streamlit as st
from utils.state_manager import init_session_state, has_personas
from utils.constants import MAX_SURVEY_QUESTIONS
from components.survey_grid import survey_grid
from services.api_client import run_survey_question
from styles.theme import load_css

st.set_page_config(page_title="Survey Mode", layout="wide")
init_session_state()

css = load_css("styles/custom.css")
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.markdown('<div class="eyebrow">Structured Questionnaire</div>', unsafe_allow_html=True)
st.title("Survey Mode")

if not has_personas():
    st.warning("No personas yet. Create an experiment first.")
    if st.button("Go to Experiment Workspace"):
        st.switch_page("pages/1_Experiment_Workspace.py")
    st.stop()

st.caption(f"Experiment: **{st.session_state.experiment['product_name']}**")

if not st.session_state.survey_questions:
    st.markdown('<div class="section-label">Set Up Your Survey</div>', unsafe_allow_html=True)
    default_q = "How likely are you to use this product?"
    with st.form("question_setup"):
        q_text = st.text_area(
            "Enter one question per line (max %d)" % MAX_SURVEY_QUESTIONS,
            value=default_q, height=100,
        )
        start = st.form_submit_button("Start Survey", type="primary")
    if start:
        questions = [q.strip() for q in q_text.split("\n") if q.strip()][:MAX_SURVEY_QUESTIONS]
        if not questions:
            st.error("Please enter at least one question.")
        else:
            st.session_state.survey_questions = questions
            st.session_state.current_question_index = 0
            st.rerun()
    st.stop()

questions = st.session_state.survey_questions
idx = st.session_state.current_question_index
total = len(questions)

st.progress((idx) / total if total else 0)
st.markdown(f'<div class="section-label">Question {idx + 1} / {total}</div>', unsafe_allow_html=True)
st.markdown(f"#### \u201c{questions[idx]}\u201d")

if idx not in st.session_state.survey_responses:
    with st.spinner("Collecting persona responses..."):
        st.session_state.survey_responses[idx] = run_survey_question(
            st.session_state.personas, questions[idx], question_idx=idx
        )

survey_grid(st.session_state.personas, st.session_state.survey_responses[idx])

st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    if idx > 0 and st.button("← Previous Question"):
        st.session_state.current_question_index -= 1
        st.rerun()
with col2:
    if idx < total - 1:
        if st.button("Next Question →", type="primary"):
            st.session_state.current_question_index += 1
            st.rerun()
    else:
        st.success("All questions answered!")
with col3:
    if st.button("View Insights"):
        st.switch_page("pages/5_Insights_Dashboard.py")

st.markdown('<div class="section-label">Ask Another Question</div>', unsafe_allow_html=True)
with st.form("add_question", clear_on_submit=True):
    new_q = st.text_input("Type a new question to ask all personas")
    add = st.form_submit_button("Add & Ask")
if add:
    new_q = new_q.strip()
    if not new_q:
        st.error("Please enter a question.")
    elif len(st.session_state.survey_questions) >= MAX_SURVEY_QUESTIONS:
        st.error(f"Maximum of {MAX_SURVEY_QUESTIONS} questions per survey reached.")
    else:
        st.session_state.survey_questions.append(new_q)
        st.session_state.current_question_index = len(st.session_state.survey_questions) - 1
        st.rerun()
