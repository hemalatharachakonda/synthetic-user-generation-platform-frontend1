"""Generates a downloadable PDF research report using reportlab.

Chart images are rendered via matplotlib (pure Python, no browser/Chrome
dependency — unlike newer Plotly+kaleido versions, which require a separate
Chrome download that isn't available in Streamlit Cloud's container) so the
PDF shows the same adoption/sentiment/theme charts visible in the in-app
report, not just tables.
"""

import io
from datetime import date

import matplotlib
matplotlib.use("Agg")  # headless backend — no display needed, safe for server-side rendering
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)

from styles.theme import SENTIMENT_COLORS, ACCENT, ACCENT_DARK, ACCENT_TINT_STRONG, INK_SOFT

CONTENT_WIDTH = 6.5 * inch  # letter page minus 0.75in margins... matches doc margins below

# reportlab's built-in Helvetica font only supports the WinAnsi character set —
# it silently renders anything outside that as a missing-glyph box (looks like a
# solid black square) instead of erroring. Groq occasionally returns "smart"
# Unicode punctuation that falls outside WinAnsi — most commonly a non-breaking
# hyphen (U+2011) in tags like "Value‑Seeker" instead of a plain ASCII hyphen —
# which is exactly what produced the black squares in the Persona Profiles table.
# Known offenders get mapped to a safe equivalent; anything else that still
# can't be encoded gets replaced with '?' as a last resort, so a font gap shows
# up as an obviously-wrong character instead of an invisible black box.
_PDF_UNSAFE_CHAR_MAP = {
    "\u2010": "-",   # hyphen
    "\u2011": "-",   # non-breaking hyphen
    "\u2012": "-",   # figure dash
    "\u2015": "-",   # horizontal bar
    "\u2212": "-",   # minus sign
    "\u200b": "",    # zero-width space
    "\u200c": "",    # zero-width non-joiner
    "\u200d": "",    # zero-width joiner
    "\ufeff": "",    # BOM / zero-width no-break space
}


def _pdf_safe(text) -> str:
    """Sanitizes any dynamic (often LLM-generated) text before it goes into a
    reportlab Paragraph/Table cell, so unsupported Unicode punctuation can't
    render as a black missing-glyph box."""
    s = str(text)
    for bad, good in _PDF_UNSAFE_CHAR_MAP.items():
        s = s.replace(bad, good)
    return s.encode("cp1252", errors="replace").decode("cp1252")


def _mpl_fig_to_image(fig, width_in=6.5, height_in=3.0):
    """Renders a matplotlib figure to a reportlab Image flowable via a PNG buffer."""
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width_in * inch, height=height_in * inch)


def _adoption_chart_image(personas: list[dict]):
    if not personas:
        return None
    names = [p["name"] for p in personas]
    scores = [p["adoption_score"] for p in personas]
    colors_list = [ACCENT_DARK if s >= 7 else ACCENT_TINT_STRONG if s >= 4 else INK_SOFT for s in scores]

    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    ax.bar(names, scores, color=colors_list)
    ax.set_title("Adoption Score by Persona", fontsize=12, fontweight="bold")
    ax.set_ylabel("Likelihood (1-10)")
    ax.set_ylim(0, 10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right", fontsize=8)
    return _mpl_fig_to_image(fig)


def _sentiment_chart_image(sentiment: dict):
    if not sentiment:
        return None
    labels = list(sentiment.keys())
    values = list(sentiment.values())
    pie_colors = [SENTIMENT_COLORS.get(label, ACCENT) for label in labels]

    fig, ax = plt.subplots(figsize=(6.5, 3.0))
    wedges, texts, autotexts = ax.pie(
        values, labels=labels, colors=pie_colors, autopct="%1.0f%%",
        wedgeprops=dict(width=0.45), startangle=90,
    )
    ax.set_title("Sentiment Breakdown", fontsize=12, fontweight="bold")
    return _mpl_fig_to_image(fig)


def _theme_chart_image(themes: list[dict]):
    if not themes:
        return None
    theme_labels = [t["theme"] for t in themes][::-1]
    pcts = [t["mentions_pct"] for t in themes][::-1]

    fig, ax = plt.subplots(figsize=(6.5, 2.6))
    ax.barh(theme_labels, pcts, color=ACCENT_DARK)
    ax.set_title("Themes Mentioned", fontsize=12, fontweight="bold")
    ax.set_xlabel("% Mentioned")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return _mpl_fig_to_image(fig, height_in=2.6)


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
        return Paragraph(_pdf_safe(text), header_style if header else cell_style)

    story = []
    story.append(Paragraph("Synthetic User Research Report", title_style))
    story.append(Paragraph(f"Product: {_pdf_safe(experiment.get('product_name', ''))}", body))
    story.append(Paragraph(f"Date: {date.today().strftime('%B %d, %Y')}", body))
    story.append(Spacer(1, 0.25 * inch))

    story.append(Paragraph("Executive Summary", h2))
    would_use = insights.get("would_use_pct", "N/A")
    would_pay = insights.get("would_pay_pct", "N/A")
    story.append(Paragraph(
        f"{would_use}% of simulated target users indicated they would use "
        f"{_pdf_safe(experiment.get('product_name', 'this product'))}, and {would_pay}% "
        f"indicated willingness to pay. Full theme and sentiment breakdown follows.",
        body))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Methodology", h2))
    story.append(Paragraph(
        f"{len(personas)} synthetic personas were generated based on the target "
        f"audience description: \"{_pdf_safe(experiment.get('target_audience', ''))}\". "
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
            f"\u2022 {_pdf_safe(theme.get('theme'))} — mentioned by {theme.get('mentions_pct')}% of personas", body))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("What Users Want & Suggested Improvements", h2))
    user_wants_summary = insights.get("user_wants_summary", "")
    if user_wants_summary:
        story.append(Paragraph(_pdf_safe(user_wants_summary), body))
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
        story.append(Paragraph(f"\u201c{_pdf_safe(q.get('quote'))}\u201d — {_pdf_safe(q.get('persona'))}", body))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
