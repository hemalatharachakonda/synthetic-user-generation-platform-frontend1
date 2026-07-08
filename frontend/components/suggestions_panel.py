import html
import streamlit as st


def render_user_wants_summary(summary: str):
    """Plain-English 'what users want' takeaway, styled as a highlighted band."""
    if not summary:
        return
    # NOTE: kept as compact single-line HTML (no leading indentation/newlines).
    # Streamlit's markdown renderer treats 4+ leading spaces as a Markdown code
    # block, so indented multi-line HTML can silently fall back to being
    # displayed as literal text instead of rendering.
    markup = (
        '<div class="insight-summary-band">'
        '<span class="im-summary-label">What Users Want</span>'
        f'<p>{html.escape(summary)}</p>'
        '</div>'
    )
    st.markdown(markup, unsafe_allow_html=True)


def render_suggestions(suggestions: list[dict]):
    """Ranked, scannable list of concrete suggestions with priority + category + who raised it."""
    if not suggestions:
        st.info("No suggestions yet — run an interview or survey first, then recalculate insights.")
        return

    cards = []
    for i, s in enumerate(suggestions, start=1):
        priority = (s.get("priority") or "low").lower()
        if priority not in ("high", "medium", "low"):
            priority = "low"
        category = html.escape(s.get("category", "General"))
        suggestion_text = html.escape(s.get("suggestion", ""))
        personas = s.get("personas") or []
        mentioned = f"Raised by {', '.join(html.escape(p) for p in personas)}" if personas else ""
        mentioned_span = f'<span class="mentioned-by">{mentioned}</span>' if mentioned else ""

        # Compact single-line HTML per card — see note above. Joining
        # indented triple-quoted fragments is what caused only the first
        # card to render while the rest showed up as raw code text.
        cards.append(
            '<div class="suggestion-card">'
            f'<div class="suggestion-rank">{i:02d}</div>'
            '<div class="suggestion-body">'
            f'<div class="suggestion-title">{suggestion_text}</div>'
            '<div class="suggestion-meta">'
            f'<span class="priority-badge priority-{priority}">{priority}</span>'
            f'<span class="category-pill">{category}</span>'
            f'{mentioned_span}'
            '</div>'
            '</div>'
            '</div>'
        )

    st.markdown(
        f'<div class="suggestion-list">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )
