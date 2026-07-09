"""Generates a downloadable PDF research report using reportlab.

Chart images are rendered via Plotly + kaleido (a headless, pure-Python static
image exporter — no browser/Chrome dependency) so the PDF shows the same
adoption/sentiment/theme charts visible in the in-app report, not just tables.
"""

import io
from datetime import date

import pandas as pd
import plotly.express as px
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)

from styles.theme import SENTIMENT_COLORS, CONTINUOUS_SCALE, ACCENT, ACCENT_DARK

CONTENT_WIDTH = 6.5 * inch  # letter page minus 0.75in margins... matches doc margins below


def _fig_to_image(fig, width_in=6.5, height_in=3.2):
    """Renders a Plotly figure to a reportlab Image flowable via a PNG buffer."""
    fig.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(l=40, r=20, t=40, b=40), showlegend=True,
    )
    png_bytes = fig.to_image(format="png", width=int(width_in * 130), height=int(height_in * 130), scale=1.5)
    return Image(io.BytesIO(png_bytes), width=width_in * inch, height=height_in * inch)


def _adoption_chart_image(personas: list[dict]):
    if not personas:
        return None
    df = pd.DataFrame([{"name": p["name"], "adoption_score": p["adoption_score"]} for p in personas])
    fig = px.bar(
        df, x="name", y="adoption_score", color="adoption_score",
        title="Adoption Score by Persona",
        labels={"adoption_score": "Likelihood (1-10)", "name": ""},
        color_continuous_scale=CONTINUOUS_SCALE,
    )
    fig.update_traces(marker_line_width=0)
    fig.update_layout(coloraxis_showscale=False)
    return _fig_to_image(fig)


def _sentiment_chart_image(sentiment: dict):
    if not sentiment:
        return None
    df = pd.DataFrame({"label": list(sentiment.keys()), "pct": list(sentiment.values())})
    fig = px.pie(
        df, names="label", values="pct", hole=0.5, title="Sentiment Breakdown",
        color="label", color_discrete_map=SENTIMENT_COLORS,
    )
    return _fig_to_image(fig, height_in=3.0)


def _theme_chart_image(themes: list[dict]):
    if not themes:
        return None
    df = pd.DataFrame(themes)
    fig = px.bar(
        df, x="mentions_pct", y="theme", orientation="h",
        title="Themes Mentioned", labels={"mentions_pct": "% Mentioned", "theme": ""},
        color_discrete_sequence=[ACCENT_DARK],
    )
    fig.update_layout(yaxis=dict(autorange="reversed"))
    return _fig_to_image(fig, height_in=2.6)


def build_report_pdf(experiment: dict, personas: list[dict], insights: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                             topMargin=0.75 * inch, bottomMargin=0.75 * inch,
                             leftMargin=0.75 * inch, rightMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontSize=20)
    h2 = styles["Heading2"]
    body = styles["BodyText"]
    # Small wrapping style for table cells — using plain strings in reportlab
    # Tables does NOT wrap text, it overflows into neighboring cells instead,
    # which is what caused the garbled/overlapping text. Wrapping every cell
    # in a Paragraph makes each cell wrap properly within its column width.
    cell_style = ParagraphStyle("Cell", parent=styles["BodyText"], fontSize=8, leading=10)
    header_style = ParagraphStyle("CellHeader", parent=styles["BodyText"], fontSize=8, leading=10,
                                   textColor=colors.white, fontName="Helvetica-Bold")

    def cell(text, header=False):
        return Paragraph(str(text), header_style if header else cell_style)

    story = []
    story.append(Paragraph("Synthetic User Research Report", title_style))
    story.append(Paragraph(f"Product: {experiment.get('product_name', '')}", body))
    story.append(Paragraph(f"Date: {date.today().strftime('%B %d, %Y')}", body))
    story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph("Executive Summary", h2))
    would_use = insights.get("would_use_pct", "N/A")
    would_pay = insights.get("would_pay_pct", "N/A")
    story.append(Paragraph(
        f"{would_use}% of simulated target users indicated they would use "
        f"{experiment.get('product_name', 'this product')}, and {would_pay}% "
        f"indicated willingness to pay. Full theme and sentiment breakdown follows.",
        body))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Methodology", h2))
    story.append(Paragraph(
        f"{len(personas)} synthetic personas were generated based on the target "
        f"audience description: \"{experiment.get('target_audience', '')}\". "
        f"Personas were surveyed and/or interviewed to gather feedback aligned "
        f"with the stated research objectives.", body))
    story.append(Spacer(1, 0.25 * inch))

    # ── Charts — the visual core, matching the in-app report ────────────────
    story.append(Paragraph("Adoption & Sentiment", h2))
    adoption_img = _adoption_chart_image(personas)
    if adoption_img:
        story.append(adoption_img)
        story.append(Spacer(1, 0.15 * inch))
    sentiment_img = _sentiment_chart_image(insights.get("sentiment", {}))
    if sentiment_img:
        story.append(sentiment_img)
        story.append(Spacer(1, 0.15 * inch))
    theme_img = _theme_chart_image(insights.get("themes", []))
    if theme_img:
        story.append(theme_img)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Persona Profiles", h2))
    persona_table_data = [[cell("Name", True), cell("Age", True), cell("Occupation", True),
                            cell("Adoption Score", True), cell("Tags", True)]]
    for p in personas:
        persona_table_data.append([
            cell(p.get("name", "")), cell(p.get("age", "")), cell(p.get("occupation", "")),
            cell(f"{p.get('adoption_score', '')}/10"), cell(", ".join(p.get("tags", []))),
        ])
    t = Table(persona_table_data, hAlign="LEFT", repeatRows=1,
               colWidths=[1.1 * inch, 0.5 * inch, 1.6 * inch, 0.9 * inch, 2.4 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2BA79B")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Key Insights", h2))
    for theme in insights.get("themes", []):
        story.append(Paragraph(
            f"• {theme.get('theme')} — mentioned by {theme.get('mentions_pct')}% of personas", body))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("What Users Want & Suggested Improvements", h2))
    user_wants_summary = insights.get("user_wants_summary", "")
    if user_wants_summary:
        story.append(Paragraph(user_wants_summary, body))
        story.append(Spacer(1, 0.1 * inch))
    suggestions = insights.get("suggestions", [])
    if suggestions:
        suggestion_table_data = [[cell("#", True), cell("Suggestion", True), cell("Category", True),
                                    cell("Priority", True), cell("Raised By", True)]]
        for i, s in enumerate(suggestions, start=1):
            suggestion_table_data.append([
                cell(i),
                cell(s.get("suggestion", "")),
                cell(s.get("category", "")),
                cell((s.get("priority", "") or "").upper()),
                cell(", ".join(s.get("personas", []) or [])),
            ])
        st_table = Table(suggestion_table_data, hAlign="LEFT", repeatRows=1,
                          colWidths=[0.3 * inch, 2.3 * inch, 0.85 * inch, 0.65 * inch, 2.4 * inch])
        st_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2BA79B")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(st_table)
    else:
        story.append(Paragraph("No suggestions available yet.", body))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Key Quotes", h2))
    for q in insights.get("key_quotes", []):
        story.append(Paragraph(f"\u201c{q.get('quote')}\u201d — {q.get('persona')}", body))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
