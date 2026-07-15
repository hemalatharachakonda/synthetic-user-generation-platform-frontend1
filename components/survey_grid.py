import streamlit as st
from services.data_processor import compute_overall_sentiment_pct
from styles.theme import score_tier


def survey_grid(personas: list[dict], responses: dict):
    """Displays the persona x question response log as a side-by-side comparison
    grid — one column per persona — so answers can be scanned across at a glance.
    Wraps into rows of up to 4 columns so it stays readable with more personas."""
    MAX_COLS_PER_ROW = 4

    for row_start in range(0, len(personas), MAX_COLS_PER_ROW):
        row_personas = personas[row_start:row_start + MAX_COLS_PER_ROW]
        cols = st.columns(len(row_personas))

        for col, p in zip(cols, row_personas):
            r = responses.get(p["id"], {})
            score = r.get("score", "-")
            comment = r.get("comment", "")
            tier = score_tier(score) if isinstance(score, (int, float)) else "mid"
            tier_class = {"high": "score-high", "mid": "score-mid", "low": "score-low"}[tier]

            with col:
                with st.container(border=True):
                    st.markdown(
                        f'<span class="score-badge {tier_class}">{score}/10</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"**{p['name']}**")
                    st.caption(f"{p['age']} · {p['occupation']}")
                    st.markdown(
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
