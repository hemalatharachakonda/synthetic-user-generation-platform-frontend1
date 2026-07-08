import streamlit as st
from services.api_client import get_persona_response

SUGGESTED_QUESTIONS = [
    "What features would make you switch to this?",
    "How much would you pay monthly?",
    "What's your biggest concern about this product?",
    "How does this compare to what you use today?",
]


def chat_interface(persona: dict):
    """Renders the full chat UI for one persona and handles sending messages."""
    persona_id = persona["id"]
    if persona_id not in st.session_state.chat_history:
        st.session_state.chat_history[persona_id] = []

    history = st.session_state.chat_history[persona_id]

    chat_container = st.container(height=400)
    with chat_container:
        for message in history:
            role = "user" if message["role"] == "user" else "assistant"
            with st.chat_message(role):
                st.write(message["content"])

    st.caption("Try asking: " + " · ".join(f"\"{q}\"" for q in SUGGESTED_QUESTIONS[:2]))

    prompt = st.chat_input(f"Ask {persona['name']} a question...")
    if prompt:
        history.append({"role": "user", "content": prompt})
        with st.spinner(f"{persona['name']} is thinking..."):
            response = get_persona_response(persona, prompt, history)
        history.append({"role": "assistant", "content": response})
        st.rerun()
