import streamlit as st
from services.data_processor import compute_overall_sentiment_pct
from styles.theme import score_tier


def survey_grid(personas: list[dict], responses: dict):
    """Displays each persona's answer to the current survey question as a
    vertical list — full-width rows, easiest to read for longer answers."""
    for p in personas:
        r = responses.get(p["id"], {})
        score = r.get("score", "-")
        comment = r.get("comment", "")
        tier = score_tier(score) if isinstance(score, (int, float)) else "mid"
        tier_class = {"high": "score-high", "mid": "score-mid", "low": "score-low"}[tier]

        with st.container(border=True):
            st.markdown(
                f'<div style="background: var(--surface); border-radius: 10px; '
                f'padding: 0.6rem 0.8rem;">'
                f'<span class="score-badge {tier_class}">{score}/10</span> '
                f'<span style="color: var(--ink); font-weight: 700; font-size: 1.02rem;">{p["name"]}</span>'
                f'<div style="color: var(--ink-soft); font-size: 0.85rem; margin: 0.15rem 0 0.5rem 0;">'
                f'{p["age"]} · {p["occupation"]} · {p.get("location", "")}</div>'
                f'<div style="color: var(--ink); font-style: italic;">\u201c{comment}\u201d</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    pct = compute_overall_sentiment_pct(responses)
    if pct >= 60:
        st.success(f"Mostly Positive — {pct}% would use")
    elif pct >= 40:
        st.warning(f"Mixed Response — {pct}% would use")
    else:
        st.error(f"Mostly Negative — {pct}% would use")
