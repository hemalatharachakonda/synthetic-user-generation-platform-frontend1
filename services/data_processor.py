"""Helpers that reshape raw persona/survey/insight data for display and charts."""

import pandas as pd

_POSITIVE_WORDS = [
    "love", "great", "excellent", "amazing", "yes", "definitely", "excited",
    "convenient", "helpful", "useful", "easy", "worth", "would use", "sign up",
    "impressed", "fantastic", "perfect", "trust", "interested", "recommend",
]
_NEGATIVE_WORDS = [
    "expensive", "concern", "worried", "no", "not sure", "confusing", "difficult",
    "hesitant", "skeptical", "won't", "wouldn't", "unlikely", "doubt", "risky",
    "complicated", "steep", "distrust", "avoid", "disappointed", "waste",
]


def score_from_answer_text(answer: str, confidence: float = 0.7) -> int:
    """Derives a rough 1-10 adoption-style score from a free-text survey
    answer, since the backend returns an answer + a self-reported model
    confidence (0-1) rather than a numeric score. This is a simple keyword
    heuristic, not sentiment analysis — good enough for a comparison badge,
    not a substitute for the actual text (always shown alongside it)."""
    text = (answer or "").lower()
    pos_hits = sum(1 for w in _POSITIVE_WORDS if w in text)
    neg_hits = sum(1 for w in _NEGATIVE_WORDS if w in text)

    baseline = 5.5 + (pos_hits - neg_hits) * 1.1
    # Confidence nudges the score away from the middle rather than setting it
    # directly — a confident positive answer scores higher, a confident
    # negative answer scores lower, but confidence alone never implies "good".
    if pos_hits > neg_hits:
        baseline += (confidence - 0.5) * 2
    elif neg_hits > pos_hits:
        baseline -= (confidence - 0.5) * 2

    return int(round(max(1, min(10, baseline))))


def segment_breakdown(personas: list[dict]) -> list[dict]:
    """Groups personas into segments (by occupation, the clearest natural
    grouping already on every persona) and aggregates 'would use this
    product' for each segment: avg score, % who'd adopt (score >= 6), and
    the segment's most common traits (used to ground a plain-English
    reasoning line — locally here, or replaced by real Groq reasoning in
    api_client.py when a key is configured)."""
    if not personas:
        return []

    groups: dict[str, list[dict]] = {}
    for p in personas:
        groups.setdefault(p.get("occupation", "Unspecified"), []).append(p)

    segments = []
    for occupation, members in groups.items():
        scores = [m.get("adoption_score", 5) for m in members]
        avg_score = round(sum(scores) / len(scores), 1)
        would_use_pct = round(sum(1 for s in scores if s >= 6) / len(scores) * 100)

        tag_counts: dict[str, int] = {}
        for m in members:
            for tag in m.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        top_traits = sorted(tag_counts, key=tag_counts.get, reverse=True)[:2]

        if avg_score >= 7:
            tone = "responded positively"
        elif avg_score >= 5:
            tone = "gave a mixed response"
        else:
            tone = "responded skeptically"
        trait_phrase = f", largely shaped by being {' and '.join(t.lower() for t in top_traits)}" if top_traits else ""
        reasoning = f"This segment {tone} (avg {avg_score}/10){trait_phrase}."

        segments.append({
            "segment": occupation,
            "count": len(members),
            "avg_score": avg_score,
            "would_use_pct": would_use_pct,
            "top_traits": top_traits,
            "reasoning": reasoning,
        })

    return sorted(segments, key=lambda s: s["avg_score"], reverse=True)


def compute_agreement_patterns(personas: list[dict], survey_responses: dict) -> list[dict]:
    """For each survey question, measures how much personas agreed or
    disagreed with each other (based on score spread), so a question with
    near-unanimous scores reads differently from one that split the panel."""
    patterns = []
    for q_idx, responses in (survey_responses or {}).items():
        scores = [r.get("score") for r in responses.values() if isinstance(r.get("score"), (int, float))]
        if len(scores) < 2:
            continue
        spread = max(scores) - min(scores)
        avg = round(sum(scores) / len(scores), 1)
        if spread <= 2:
            level = "Strong agreement"
        elif spread <= 5:
            level = "Mixed opinions"
        else:
            level = "Polarized — split panel"
        patterns.append({
            "question_index": q_idx,
            "level": level,
            "avg_score": avg,
            "spread": spread,
            "respondents": len(scores),
        })
    return patterns


def compute_behavioral_trends(personas: list[dict]) -> list[dict]:
    """Finds traits that correlate with higher or lower adoption scores
    across the panel — e.g. personas tagged 'skeptical' scoring notably
    lower on average than the rest of the panel. Needs at least a couple
    personas per trait to be meaningful, so thin panels return []."""
    if len(personas) < 3:
        return []

    overall_avg = sum(p.get("adoption_score", 5) for p in personas) / len(personas)
    tag_scores: dict[str, list[float]] = {}
    for p in personas:
        for tag in p.get("tags", []):
            tag_scores.setdefault(tag, []).append(p.get("adoption_score", 5))

    trends = []
    for tag, scores in tag_scores.items():
        if len(scores) < 2:
            continue
        tag_avg = sum(scores) / len(scores)
        diff = tag_avg - overall_avg
        if abs(diff) < 1.0:
            continue  # not a meaningful trend, close to the panel average
        direction = "score higher" if diff > 0 else "score lower"
        trends.append({
            "trait": tag,
            "avg_score": round(tag_avg, 1),
            "diff": round(diff, 1),
            "count": len(scores),
            "summary": f"Personas tagged \u201c{tag}\u201d {direction} than average "
                       f"({round(tag_avg, 1)}/10 vs {round(overall_avg, 1)}/10 overall).",
        })
    return sorted(trends, key=lambda t: abs(t["diff"]), reverse=True)[:5]


def personas_to_dataframe(personas: list[dict]) -> pd.DataFrame:
    if not personas:
        return pd.DataFrame(columns=["name", "age", "occupation", "adoption_score", "tags"])
    return pd.DataFrame([
        {
            "name": p["name"],
            "age": p["age"],
            "occupation": p["occupation"],
            "adoption_score": p["adoption_score"],
            "tags": ", ".join(p.get("tags", [])),
        }
        for p in personas
    ])


def survey_question_to_dataframe(personas: list[dict], responses: dict) -> pd.DataFrame:
    """responses: {persona_id: {"score":.., "comment":..}}"""
    rows = []
    for p in personas:
        r = responses.get(p["id"], {})
        rows.append({
            "Persona": f"{p['name']}, {p['age']}",
            "Score": r.get("score", "-"),
            "Comment": r.get("comment", ""),
        })
    return pd.DataFrame(rows)


def compute_overall_sentiment_pct(responses: dict) -> float:
    """Given {persona_id: {"score": int, ...}}, returns % with score >= 6."""
    if not responses:
        return 0.0
    scores = [r["score"] for r in responses.values() if "score" in r]
    if not scores:
        return 0.0
    positive = sum(1 for s in scores if s >= 6)
    return round((positive / len(scores)) * 100)


def themes_to_dataframe(themes: list[dict]) -> pd.DataFrame:
    if not themes:
        return pd.DataFrame(columns=["theme", "mentions_pct"])
    return pd.DataFrame(themes)
