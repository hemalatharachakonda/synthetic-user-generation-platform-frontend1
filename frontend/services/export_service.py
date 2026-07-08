"""Generates a downloadable PDF research report using reportlab."""

import io
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)


def build_report_pdf(experiment: dict, personas: list[dict], insights: dict) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                             topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleCustom", parent=styles["Title"], fontSize=20)
    h2 = styles["Heading2"]
    body = styles["BodyText"]

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
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Persona Profiles", h2))
    persona_table_data = [["Name", "Age", "Occupation", "Adoption Score", "Tags"]]
    for p in personas:
        persona_table_data.append([
            p.get("name", ""), str(p.get("age", "")), p.get("occupation", ""),
            f"{p.get('adoption_score', '')}/10", ", ".join(p.get("tags", []))
        ])
    t = Table(persona_table_data, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4CAF50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
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
        suggestion_table_data = [["#", "Suggestion", "Category", "Priority", "Raised By"]]
        for i, s in enumerate(suggestions, start=1):
            suggestion_table_data.append([
                str(i),
                s.get("suggestion", ""),
                s.get("category", ""),
                (s.get("priority", "") or "").upper(),
                ", ".join(s.get("personas", []) or []),
            ])
        st_table = Table(suggestion_table_data, hAlign="LEFT", repeatRows=1,
                          colWidths=[0.25 * inch, 2.6 * inch, 0.9 * inch, 0.7 * inch, 1.55 * inch])
        st_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2BA79B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
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
