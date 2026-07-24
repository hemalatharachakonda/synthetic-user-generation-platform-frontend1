import streamlit as st
from datetime import date
from components.suggestions_panel import render_user_wants_summary, render_suggestions
from components.visualizations import adoption_chart, sentiment_donut, theme_bars


def _score_tier_label(score: float) -> str:
    if score >= 7:
        return "score-high"
    if score >= 4:
        return "score-mid"
    return "score-low"


def report_preview(experiment: dict, personas: list[dict], insights: dict):
    # ── Header ────────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div class="specimen-card" style="padding: 1.4rem 1.6rem;">
            <div class="eyebrow">Synthetic User Research Report</div>
            <h2 style="margin: 0.3rem 0 0.1rem 0;">{experiment.get('product_name', '')}</h2>
            <div class="specimen-meta">Filed {date.today().strftime('%B %d, %Y')} ·
            {len(personas)} synthetic personas surveyed</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Executive KPI row — the numbers a stakeholder reads first ─────────
    would_use = insights.get("would_use_pct", 0)
    would_pay = insights.get("would_pay_pct", 0)
    avg_adoption = round(sum(p.get("adoption_score", 0) for p in personas) / len(personas), 1) if personas else 0
    # "Top Theme" must be the theme with the highest mentions_pct — not just
    # whichever one happens to come first in the list, since nothing guarantees
    # Groq (or the mock fallback) returns themes pre-sorted by percentage.
    themes = insights.get("themes") or []
    top_theme = max(themes, key=lambda t: t.get("mentions_pct", 0)).get("theme", "—") if themes else "—"

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Would Use It", f"{would_use}%")
    k2.metric("Would Pay For It", f"{would_pay}%")
    k3.metric("Avg. Adoption Score", f"{avg_adoption}/10")
    k4.metric("Top Theme", top_theme)

    with st.container(border=True):
        st.markdown('<div class="section-label">Executive Summary</div>', unsafe_allow_html=True)
        verdict = (
            "strong product-market signal" if would_use >= 65 else
            "mixed but workable signal" if would_use >= 40 else
            "weak signal — significant rework likely needed"
        )
        st.write(
            f"**{would_use}%** of the target audience for **{experiment.get('product_name', 'this product')}** "
            f"said they would use it, and **{would_pay}%** said they'd actually pay for it — "
            f"overall this reads as a **{verdict}**. The panel's average adoption score was "
            f"**{avg_adoption}/10**. The sections below break down *why*, using the actual "
            f"themes, sentiment, and quotes the synthetic panel gave."
        )

    # ── Charts — the visual core of the report ─────────────────────────────
    st.markdown('<div class="section-label">Adoption & Sentiment</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])
    with c1:
        with st.container(border=True):
            adoption_chart(personas)
    with c2:
        with st.container(border=True):
            sentiment_donut(insights.get("sentiment", {}))

    with st.container(border=True):
        st.markdown('<div class="section-label">Themes Mentioned</div>', unsafe_allow_html=True)
        theme_bars(insights.get("themes", []))

    # ── Persona highlights — best and most skeptical, not just a full list ─
    with st.container(border=True):
        st.markdown('<div class="section-label">Persona Highlights</div>', unsafe_allow_html=True)
        sorted_personas = sorted(personas, key=lambda p: p.get("adoption_score", 0), reverse=True)
        best = sorted_personas[:2]
        worst = sorted_personas[-2:] if len(sorted_personas) > 2 else []

        if best:
            st.markdown("**Strongest advocates**")
            for p in best:
                tier = _score_tier_label(p.get("adoption_score", 0))
                st.markdown(
                    f'{p["name"]}, {p.get("age","")} — {p.get("occupation","")} '
                    f'<span class="score-badge {tier}">{p.get("adoption_score", 0)}/10</span>',
                    unsafe_allow_html=True,
                )
                st.caption(p.get("bio", ""))
        if worst:
            st.markdown("**Most skeptical**")
            for p in worst:
                tier = _score_tier_label(p.get("adoption_score", 0))
                st.markdown(
                    f'{p["name"]}, {p.get("age","")} — {p.get("occupation","")} '
                    f'<span class="score-badge {tier}">{p.get("adoption_score", 0)}/10</span>',
                    unsafe_allow_html=True,
                )
                st.caption(p.get("bio", ""))

        with st.expander(f"View all {len(personas)} personas"):
            for p in personas:
                tier = _score_tier_label(p.get("adoption_score", 0))
                st.markdown(
                    f'{p["name"]}, {p.get("age","")} — {p.get("occupation","")} '
                    f'<span class="score-badge {tier}">{p.get("adoption_score", 0)}/10</span>',
                    unsafe_allow_html=True,
                )

    # ── What users want / suggestions — the actionable part ────────────────
    with st.container(border=True):
        st.markdown('<div class="section-label">What Users Want & Suggested Improvements</div>', unsafe_allow_html=True)
        render_user_wants_summary(insights.get("user_wants_summary", ""))
        render_suggestions(insights.get("suggestions", []))

    # ── Key quotes — grounding the numbers in real voice ───────────────────
    with st.container(border=True):
        st.markdown('<div class="section-label">Key Quotes</div>', unsafe_allow_html=True)
        quotes = insights.get("key_quotes", [])
        if not quotes:
            st.caption("No quotes captured yet — run Interview Mode or Survey Mode for more grounded quotes here.")
        for q in quotes:
            st.write(f"> \"{q['quote']}\" — *{q['persona']}*")

    # ── Recommendation — the closing takeaway a stakeholder wants ──────────
    with st.container(border=True):
        st.markdown('<div class="section-label">Recommendation</div>', unsafe_allow_html=True)
        if would_use >= 65:
            st.success(
                f"**Proceed.** Adoption signal is strong ({would_use}%). Focus next on "
                f"the top-mentioned theme (\"{top_theme}\") and the suggestions above to "
                f"convert the remaining skeptics."
            )
        elif would_use >= 40:
            st.warning(
                f"**Proceed with changes.** Signal is mixed ({would_use}%). Address the "
                f"concerns raised by the most skeptical personas above before committing "
                f"further budget."
            )
        else:
            st.error(
                f"**Reconsider the approach.** Adoption signal is weak ({would_use}%). "
                f"Revisit the core value proposition against the target audience before "
                f"investing further."
            )
