"""
Theme constants and Plotly template for the "Dianne" visual identity:
Blue Dianne as the single background color, bright aqua as the single accent.
Import PLOTLY_LAYOUT and apply it to every chart via fig.update_layout(**PLOTLY_LAYOUT)
so all visualizations share one consistent look.
"""

# ── Core palette (kept in sync with styles/custom.css) ───────────────────────
BG = "#204852"            # Blue Dianne — page background, used everywhere
BG_DEEP = "#152F35"
BG_SOFT = "#2A5762"

SURFACE = "#F4F7F7"        # card surface (neutral, not a design color)
SURFACE_ALT = "#E9EFEF"

INK = "#14282C"            # text on light surfaces
INK_SOFT = "#55696D"
INK_ON_DARK = "#F4F7F7"    # text on the dark background
INK_ON_DARK_SOFT = "#B9CBCE"

ACCENT = "#4FD1C5"         # the one accent color — bright aqua
ACCENT_DARK = "#2BA79B"
ACCENT_TINT = "#DEF7F4"
ACCENT_TINT_STRONG = "#A9EDE3"

BORDER = "#D7E3E3"

FONT_DISPLAY = "Sora, -apple-system, sans-serif"
FONT_BODY = "Inter, -apple-system, sans-serif"
FONT_MONO = "JetBrains Mono, SFMono-Regular, monospace"

# Sentiment / status — single accent hue at different weights, not multiple colors
SENTIMENT_COLORS = {
    "Positive": ACCENT_DARK,
    "Neutral": ACCENT_TINT_STRONG,
    "Negative": INK_SOFT,
}

SCORE_TIER_COLORS = {
    "high": ACCENT_DARK,
    "mid": ACCENT_TINT_STRONG,
    "low": INK_SOFT,
}

# Discrete colorway used for multi-series/categorical charts — shades of the one accent
COLORWAY = [ACCENT_DARK, ACCENT, ACCENT_TINT_STRONG, INK_SOFT, BORDER, BG_SOFT]

# Continuous scale used for adoption-score bar charts
CONTINUOUS_SCALE = [[0, SURFACE_ALT], [0.5, ACCENT_TINT_STRONG], [1, ACCENT_DARK]]

# Dedicated bar-chart scale — CONTINUOUS_SCALE's near-white low end (SURFACE_ALT)
# is intentional for the heatmap (fading to background = "low density"), but it
# makes low-value bars nearly invisible against a white chart background. Bars
# always need a visible fill, so this scale never goes lighter than a solid tint.
BAR_SCALE = [[0, ACCENT_TINT_STRONG], [1, ACCENT_DARK]]

# Shared Plotly layout — spread this into fig.update_layout(**PLOTLY_LAYOUT)
PLOTLY_LAYOUT = dict(
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    font=dict(family=FONT_BODY, color=INK, size=13),
    title_font=dict(family=FONT_DISPLAY, color=INK, size=17),
    colorway=COLORWAY,
    margin=dict(l=20, r=20, t=50, b=20),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)


def score_tier(score: float) -> str:
    """Returns 'high' | 'mid' | 'low' for a 0-10 adoption score."""
    if score >= 7:
        return "high"
    if score >= 4:
        return "mid"
    return "low"


def load_css(path: str = "styles/custom.css") -> str:
    """Load the CSS file.

    Resolves relative to this file's own directory (styles/) rather than the
    process's current working directory, since Streamlit Cloud runs the app
    with the repo root as cwd, not the folder containing the main script —
    a plain relative path like "styles/custom.css" silently fails there.
    """
    import os

    filename = os.path.basename(path)
    here = os.path.dirname(os.path.abspath(__file__))
    resolved = os.path.join(here, filename)
    try:
        with open(resolved, "r") as f:
            return f.read()
    except FileNotFoundError:
        return ""
