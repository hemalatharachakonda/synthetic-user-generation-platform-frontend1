import streamlit as st
from styles.theme import score_tier


def persona_card(persona: dict, on_interview=None, on_details=None):
    """Renders one persona as a 'specimen card' — the platform's signature UI element."""
    tier = score_tier(persona["adoption_score"])
    tier_class = {"high": "score-high", "mid": "score-mid", "low": "score-low"}[tier]
    specimen_id = f"SUBJECT · {persona['id'][-6:].upper()}"

    tags_html = "".join(f'<span class="tag-pill">{t}</span>' for t in persona.get("tags", []))

    with st.container(border=True):
        col1, col2 = st.columns([1, 3])
        with col1:
            avatar_url = f"https://api.dicebear.com/7.x/avataaars/svg?seed={persona.get('avatar_seed', persona['id'])}"
            st.image(avatar_url, width=64)
        with col2:
            st.markdown(
                f"""
                <div class="specimen-id">{specimen_id}</div>
                <div class="specimen-name">{persona['name']}</div>
                <div class="specimen-meta">{persona['age']} · {persona['occupation']}</div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <div style="margin: 0.6rem 0 0.3rem 0;">
                <span class="score-badge {tier_class}">{persona['adoption_score']}/10 ADOPTION</span>
            </div>
            <div style="margin-bottom: 0.4rem;">{tags_html}</div>
            """,
            unsafe_allow_html=True,
        )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Interview", key=f"int_{persona['id']}", width='stretch'):
                if on_interview:
                    on_interview(persona["id"])
        with col_b:
            if st.button("Field Notes", key=f"det_{persona['id']}", width='stretch'):
                if on_details:
                    on_details(persona["id"])
                else:
                    with st.expander("Field notes", expanded=True):
                        st.write(persona.get("bio", "No bio available."))
