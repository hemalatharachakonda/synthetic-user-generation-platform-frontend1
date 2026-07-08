"""Helpers that reshape raw persona/survey/insight data for display and charts."""

import pandas as pd


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
