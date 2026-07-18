import plotly.express as px
import pandas as pd
import streamlit as st
from styles.theme import SENTIMENT_COLORS, PLOTLY_LAYOUT, CONTINUOUS_SCALE, BAR_SCALE, ACCENT, ACCENT_DARK


def adoption_chart(personas: list[dict]):
    """Bar chart showing adoption rates per persona."""
    if not personas:
        st.info("No personas yet.")
        return
    df = pd.DataFrame([{"name": p["name"], "adoption_score": p["adoption_score"]} for p in personas])
    fig = px.bar(
        df, x="name", y="adoption_score", color="adoption_score",
        title="Would Use This Product?",
        labels={"adoption_score": "Likelihood (1-10)", "name": "Persona"},
        color_continuous_scale=BAR_SCALE,
        range_color=[1, 10],
    )
    fig.update_layout(**PLOTLY_LAYOUT, showlegend=False)
    fig.update_traces(marker_line_width=1.5, marker_line_color=ACCENT_DARK)
    st.plotly_chart(fig, width='stretch')


def sentiment_donut(sentiment: dict):
    """Donut chart for sentiment breakdown. sentiment = {"Positive": pct, "Neutral": pct, "Negative": pct}"""
    if not sentiment:
        st.info("No sentiment data yet.")
        return
    labels = list(sentiment.keys())
    values = list(sentiment.values())
    fig = px.pie(
        values=values, names=labels,
        color=labels, color_discrete_map=SENTIMENT_COLORS,
        hole=0.55, title="Sentiment Breakdown",
    )
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_traces(marker_line_color="#FFFFFF", marker_line_width=2, textfont_family="JetBrains Mono")
    st.plotly_chart(fig, width='stretch')


def theme_bars(themes: list[dict]):
    """Horizontal bar chart for theme mention frequency."""
    if not themes:
        st.info("No themes extracted yet.")
        return
    df = pd.DataFrame(themes).sort_values("mentions_pct")
    fig = px.bar(
        df, x="mentions_pct", y="theme", orientation="h",
        title="Theme Clusters", labels={"mentions_pct": "% Mentions", "theme": ""},
        color_discrete_sequence=[ACCENT],
    )
    fig.update_layout(**PLOTLY_LAYOUT, showlegend=False)
    fig.update_traces(marker_line_width=0)
    st.plotly_chart(fig, width='stretch')


def persona_segment_heatmap(personas: list[dict]):
    """Simple heat map of adoption score by occupation bucket, for the dashboard."""
    if not personas:
        st.info("No personas yet.")
        return
    df = pd.DataFrame([{"occupation": p["occupation"], "score": p["adoption_score"]} for p in personas])
    pivot = df.pivot_table(index="occupation", values="score", aggfunc="mean").reset_index()
    fig = px.density_heatmap(
        df, x="occupation", y="score", nbinsx=len(pivot),
        title="Adoption Score by Occupation",
        color_continuous_scale=CONTINUOUS_SCALE,
    )
    fig.update_layout(**PLOTLY_LAYOUT)
    st.plotly_chart(fig, width='stretch')
