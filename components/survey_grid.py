import streamlit as st
from services.data_processor import compute_overall_sentiment_pct
from styles.theme import score_tier


def survey_grid(personas: list[dict], responses: dict):
    """Displays the persona x question response log as styled specimen rows."""
    for p in personas:
        r = responses.get(p["id"], {})
        score = r.get("score", "-")
        comment = r.get("comment", "")
        tier = score_tier(score) if isinstance(score, (int, float)) else "mid"
        tier_class = {"high": "score-high", "mid": "score-mid", "low": "score-low"}[tier]

        with st.container(border=True):
            cols = st.columns([1, 4])
            cols[0].markdown(
                f'<span class="score-badge {tier_class}">{score}/10</span>',
                unsafe_allow_html=True,
            )
            cols[1].markdown(
                f"**{p['name']}**, {p['age']} · {p['occupation']}<br>"
                f"<span style='color: var(--ink-soft); font-style: italic;'>\u201c{comment}\u201d</span>",
                unsafe_allow_html=True,
            )

    pct = compute_overall_sentiment_pct(responses)
    if pct >= 60:
        st.success(f"Mostly Positive — {pct}% would use")
    elif pct >= 40:
        st.warning(f"Mixed Response — {pct}% would use")
    else:
        st.error(f"Mostly Negative — {pct}% would use")
