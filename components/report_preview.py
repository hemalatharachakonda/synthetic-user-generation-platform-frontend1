import streamlit as st
from datetime import date
from components.suggestions_panel import render_user_wants_summary, render_suggestions


def report_preview(experiment: dict, personas: list[dict], insights: dict):
    st.markdown(
        f"""
        <div class="specimen-card" style="padding: 1.4rem 1.6rem;">
            <div class="eyebrow">Synthetic User Research Report</div>
            <h2 style="margin: 0.3rem 0 0.1rem 0;">{experiment.get('product_name', '')}</h2>
            <div class="specimen-meta">Filed {date.today().strftime('%B %d, %Y')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown('<div class="section-label">Executive Summary</div>', unsafe_allow_html=True)
        st.write(
            f"{insights.get('would_use_pct', 'N/A')}% of target users would use "
            f"{experiment.get('product_name', 'the product')}, with "
            f"{insights.get('would_pay_pct', 'N/A')}% willing to pay for it. "
            f"Key opportunities and concerns are broken down below."
        )

    with st.container(border=True):
        st.markdown('<div class="section-label">Persona Profiles</div>', unsafe_allow_html=True)
        for p in personas:
            st.write(f"**{p['name']}, {p['age']}** — {p['occupation']}")
            st.caption(p.get("bio", ""))

    with st.container(border=True):
        st.markdown('<div class="section-label">Key Insights</div>', unsafe_allow_html=True)
        for theme in insights.get("themes", []):
            st.write(f"● **{theme['theme']}** is a top concern ({theme['mentions_pct']}% mentioned)")

    with st.container(border=True):
        st.markdown('<div class="section-label">What Users Want & Suggested Improvements</div>', unsafe_allow_html=True)
        render_user_wants_summary(insights.get("user_wants_summary", ""))
        render_suggestions(insights.get("suggestions", []))

    with st.container(border=True):
        st.markdown('<div class="section-label">Key Quotes</div>', unsafe_allow_html=True)
        for q in insights.get("key_quotes", []):
            st.write(f"> \"{q['quote']}\" — *{q['persona']}*")
