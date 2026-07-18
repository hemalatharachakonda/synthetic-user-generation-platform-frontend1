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
