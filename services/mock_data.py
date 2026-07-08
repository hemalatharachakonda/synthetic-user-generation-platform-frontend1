"""
Mock data generator.

This simulates what your real backend (calling Groq) will eventually return.
Every function here mirrors an endpoint in api_client.py's REAL_MODE branch,
so when USE_MOCK_DATA=False, api_client.py calls your backend instead of these
functions, and every page above it keeps working unchanged.
"""

import random
import uuid
from utils.constants import PERSONALITY_TAG_POOL, OCCUPATIONS_POOL

FIRST_NAMES = ["Sarah", "Mike", "Priya", "David", "Emma", "Raj", "Lucia",
               "Tom", "Aisha", "Noah", "Wei", "Fatima"]

SAMPLE_QUOTES_POSITIVE = [
    "This would save me hours every week!",
    "Exactly what my team has been missing.",
    "I'd recommend this to my colleagues immediately.",
    "The onboarding felt effortless.",
]
SAMPLE_QUOTES_NEUTRAL = [
    "It's fine, but I'm not sure it beats what I already use.",
    "I'd need to try it longer before deciding.",
]
SAMPLE_QUOTES_NEGATIVE = [
    "Too complex for daily use.",
    "The pricing feels steep for what it offers.",
    "I ran into a few confusing steps early on.",
]

THEMES_POOL = ["Privacy", "Speed", "Pricing", "Mobile Experience",
               "Onboarding", "Integrations", "Customer Support", "Design"]

# Concrete, actionable suggestions tied to each theme users actually raised.
# (suggestion text, category, base priority)
SUGGESTION_LIBRARY = {
    "Privacy": [
        ("Publish a plain-language privacy summary during onboarding", "Trust", "high"),
        ("Add a one-tap opt-out for data sharing with third parties", "Feature", "medium"),
    ],
    "Speed": [
        ("Optimize load times for the core workflow", "Performance", "high"),
        ("Add a lightweight or offline mode for slow connections", "Feature", "medium"),
    ],
    "Pricing": [
        ("Introduce a lower-cost tier for individuals and small teams", "Pricing", "high"),
        ("Offer an annual plan discount to ease monthly cost concerns", "Pricing", "medium"),
    ],
    "Mobile Experience": [
        ("Improve mobile responsiveness for on-the-go use", "UX", "high"),
        ("Add push notifications for key updates", "Feature", "low"),
    ],
    "Onboarding": [
        ("Simplify first-time setup with a guided walkthrough", "UX", "high"),
        ("Add sample data so users can try it before committing", "Feature", "medium"),
    ],
    "Integrations": [
        ("Add integrations with the tools people already use daily", "Feature", "high"),
        ("Provide an open API for custom integrations", "Feature", "low"),
    ],
    "Customer Support": [
        ("Add live chat support for quick questions", "Support", "medium"),
        ("Build a self-serve help center for common issues", "Support", "low"),
    ],
    "Design": [
        ("Refine the visual design for a cleaner first impression", "Design", "medium"),
        ("Add a dark mode option", "Design", "low"),
    ],
}


def generate_suggestions(personas: list[dict], themes: list[dict]) -> list[dict]:
    """Derives concrete, ranked suggestions tied to the themes users actually raised."""
    names_pool = [p["name"] for p in personas] if personas else []
    suggestions = []
    for theme in themes:
        for text, category, base_priority in SUGGESTION_LIBRARY.get(theme["theme"], []):
            mentioned_by = (
                random.sample(names_pool, k=min(len(names_pool), random.randint(1, min(3, len(names_pool)))))
                if names_pool else []
            )
            priority = base_priority if theme["mentions_pct"] >= 35 else "low"
            suggestions.append({
                "suggestion": text,
                "category": category,
                "priority": priority,
                "mentions_pct": theme["mentions_pct"],
                "personas": mentioned_by,
            })
    order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda s: order[s["priority"]])
    return suggestions[:6]


def generate_user_wants_summary(themes: list[dict], would_use_pct: int) -> str:
    if not themes:
        return "Not enough feedback yet to summarize what users want."
    top = ", ".join(t["theme"] for t in themes[:2])
    return (
        f"Across interviews and surveys, {top} came up most often as what would shape "
        f"whether people adopt this product. {would_use_pct}% said they'd use it overall, "
        f"but turning that into real adoption depends on acting on the specific requests below."
    )


def _random_avatar_seed():
    return random.randint(1, 9999)


def generate_personas(product_name: str, description: str,
                       target_audience: str, objectives: str, count: int) -> list[dict]:
    """Mocks POST /api/personas/generate"""
    personas = []
    used_names = random.sample(FIRST_NAMES, min(count, len(FIRST_NAMES)))
    for i in range(count):
        name = used_names[i] if i < len(used_names) else f"Persona {i+1}"
        age = random.randint(22, 55)
        occupation = random.choice(OCCUPATIONS_POOL)
        tags = random.sample(PERSONALITY_TAG_POOL, k=3)
        adoption_score = round(random.uniform(3.0, 9.5), 1)
        personas.append({
            "id": f"p_{uuid.uuid4().hex[:8]}",
            "name": name,
            "age": age,
            "occupation": occupation,
            "tags": tags,
            "adoption_score": adoption_score,
            "avatar_seed": _random_avatar_seed(),
            "bio": (
                f"{name} is a {age}-year-old {occupation.lower()} who fits the "
                f"target profile: {target_audience.strip()[:120]}."
            ),
        })
    return personas


def run_survey_question(personas: list[dict], question: str) -> dict:
    """Mocks POST /api/survey/run for a single question. Returns {persona_id: {score, comment}}"""
    results = {}
    for p in personas:
        score = max(1, min(10, round(random.gauss(p["adoption_score"], 1.5))))
        if score >= 7:
            comment = random.choice(SAMPLE_QUOTES_POSITIVE)
        elif score >= 4:
            comment = random.choice(SAMPLE_QUOTES_NEUTRAL)
        else:
            comment = random.choice(SAMPLE_QUOTES_NEGATIVE)
        results[p["id"]] = {"score": score, "comment": comment}
    return results


def get_persona_response(persona: dict, message: str, history: list[dict]) -> str:
    """Mocks POST /api/interview/message — a persona's conversational reply.

    Picks a canned response that's topically relevant to the question asked,
    instead of a fully random one, so "how much would you pay" doesn't get
    answered with an unrelated line about existing tools.
    """
    msg = message.lower()

    if any(w in msg for w in ["pay", "price", "cost", "$", "afford", "subscription"]):
        return "Honestly, price matters to me — I'd expect something in the $10-15/month range."
    if any(w in msg for w in ["concern", "worry", "privacy", "risk", "trust", "data"]):
        return "That's a good question. My biggest concern would be data privacy."
    if any(w in msg for w in ["mobile", "daily", "phone", "app", "often", "frequently"]):
        return "If it worked smoothly on mobile, I'd probably use it daily."
    if any(w in msg for w in ["compare", "today", "currently", "alternative", "instead", "existing"]):
        return "I like the idea, but I'd need to see how it fits with tools I already use."
    if any(w in msg for w in ["feature", "switch", "want", "need", "convince"]):
        return "As someone balancing a lot day-to-day, I'd want this to save me time, not add steps."

    canned = [
        "As someone balancing a lot day-to-day, I'd want this to save me time, not add steps.",
        "Honestly, price matters to me — I'd expect something in the $10-15/month range.",
        "I like the idea, but I'd need to see how it fits with tools I already use.",
        "That's a good question. My biggest concern would be data privacy.",
        "If it worked smoothly on mobile, I'd probably use it daily.",
    ]
    return random.choice(canned)


def extract_insights(personas: list[dict], survey_responses: dict, chat_history: dict) -> dict:
    """Mocks POST /api/insights/extract"""
    all_scores = [p["adoption_score"] for p in personas] or [0]
    would_use_pct = round((sum(1 for s in all_scores if s >= 6) / len(all_scores)) * 100)
    would_pay_pct = max(0, would_use_pct - random.randint(5, 15))

    themes = random.sample(THEMES_POOL, k=4)
    theme_data = [{"theme": t, "mentions_pct": random.randint(20, 50)} for t in themes]
    theme_data.sort(key=lambda x: x["mentions_pct"], reverse=True)

    pos = random.randint(35, 55)
    neg = random.randint(15, 30)
    neu = max(0, 100 - pos - neg)

    quotes = [
        {"quote": random.choice(SAMPLE_QUOTES_POSITIVE), "persona": random.choice(personas)["name"] if personas else "N/A"},
        {"quote": random.choice(SAMPLE_QUOTES_NEGATIVE), "persona": random.choice(personas)["name"] if personas else "N/A"},
    ]

    return {
        "would_use_pct": would_use_pct,
        "would_pay_pct": would_pay_pct,
        "themes": theme_data,
        "sentiment": {"Positive": pos, "Neutral": neu, "Negative": neg},
        "key_quotes": quotes,
        "suggestions": generate_suggestions(personas, theme_data),
        "user_wants_summary": generate_user_wants_summary(theme_data, would_use_pct),
    }
