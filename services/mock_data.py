"""
Local sample-data generator. Used as the fallback whenever Groq is
unavailable (no API key, or a call fails) for Personas, Survey, Interview,
and Insights — so the app always works even without a Groq key configured.
"""

import random
import uuid
from utils.constants import PERSONALITY_TAG_POOL, OCCUPATIONS_POOL

FIRST_NAMES = ["Sarah", "Mike", "Priya", "David", "Emma", "Raj", "Lucia",
               "Tom", "Aisha", "Noah", "Wei", "Fatima", "Ryan", "Monica",
               "Holly", "Aaron", "Kevin", "Nancy", "Brittney", "Michelle",
               "Angela", "Johnny", "Derek", "Suzanne", "Curtis", "Tamara",
               "Kenneth", "Ronald", "Shannon", "Austin", "Anthony", "Kelly"]

LAST_NAMES = ["Bowen", "Dennis", "Walter", "Curtis", "Garner", "Salinas",
              "Brooks", "Martin", "Garza", "Hunter", "Garcia", "Thompson",
              "Ruiz", "Brown", "Green", "Schmidt", "Martinez", "Bond",
              "Gonzalez", "Rachakonda", "Patel", "Kim", "Nguyen", "Cohen",
              "Rossi", "Okafor", "Ivanov", "Silva", "Khan", "Muller"]


LOCATIONS = ["Chennai", "Bengaluru", "Mumbai", "Hyderabad", "Pune", "Delhi",
             "San Francisco", "New York", "Austin", "Seattle", "Chicago",
             "Toronto", "Vancouver", "London", "Manchester", "Berlin",
             "Amsterdam", "Singapore", "Dubai", "Sydney", "Melbourne",
             "Lagos", "Nairobi", "São Paulo", "Mexico City"]


def random_roster(count: int) -> list[dict]:
    """Generates the local, deterministic part of a persona: name, occupation,
    location, avatar seed. Age, personality/adoption/bio/quote get filled in
    separately (by Groq when available, via fill_traits_locally otherwise)."""
    roster = []
    for _ in range(count):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        roster.append({
            "id": f"p_{uuid.uuid4().hex[:8]}",
            "name": f"{first} {last}",
            "occupation": random.choice(OCCUPATIONS_POOL),
            "location": random.choice(LOCATIONS),
            "avatar_seed": _random_avatar_seed(),
        })
    return roster


# Behavioral pattern (HOW they act) and psychological profile (WHY they act
# that way) per trait — used to build these fields locally without Groq, by
# combining the phrases for whichever traits a persona actually got.
_BEHAVIOR_BY_TAG = {
    "Extrovert": "talks through new tools with friends or colleagues before deciding",
    "Introvert": "prefers to quietly research and try things alone before committing",
    "Analytical": "reads reviews and compares specs in detail before any purchase",
    "Early Adopter": "actively seeks out and tries new products as soon as they launch",
    "Skeptical": "waits to see how a product performs for others before trying it",
    "Budget-Conscious": "checks pricing and looks for discounts before anything else",
    "Tech-Savvy": "explores a product's settings and features hands-on immediately",
    "Detail-Oriented": "reads the fine print and documentation before adopting a tool",
    "Impulsive Buyer": "signs up on a whim if something looks appealing in the moment",
    "Risk-Averse": "sticks with familiar tools unless given a strong, proven reason to switch",
    "Trendsetter": "wants to be first among peers to use and talk about new things",
    "Loyal Customer": "sticks with brands they already trust rather than switching often",
    "Value Seeker": "weighs cost against features carefully before deciding",
}
_PSYCHOLOGY_BY_TAG = {
    "Extrovert": "is motivated by social validation and what their circle thinks",
    "Introvert": "values independence and doesn't want to feel pressured into a decision",
    "Analytical": "fears making an uninformed choice more than missing out",
    "Early Adopter": "is driven by curiosity and the appeal of being ahead of the curve",
    "Skeptical": "has been burned by overhyped products before and guards against that",
    "Budget-Conscious": "worries about wasting money on something that won't pay off",
    "Tech-Savvy": "is motivated by mastery — wanting to fully understand a tool, not just use it",
    "Detail-Oriented": "fears hidden costs or limitations they didn't anticipate",
    "Impulsive Buyer": "is driven by instant gratification and emotional appeal",
    "Risk-Averse": "prioritizes stability and predictability over novelty",
    "Trendsetter": "is motivated by status and being seen as ahead of others",
    "Loyal Customer": "values consistency and dislikes the friction of switching tools",
    "Value Seeker": "is motivated by getting the most return for their effort or money",
}


def fill_traits_locally(roster: list[dict], target_audience: str) -> list[dict]:
    """Fills in age/tags/adoption_score/bio/behavioral_pattern/
    psychological_profile/quote for a roster using local mock logic — the
    fallback path when Groq is unavailable or fails."""
    for p in roster:
        p.setdefault("age", random.randint(22, 58))
        p["tags"] = random.sample(PERSONALITY_TAG_POOL, k=3)
        p["adoption_score"] = round(random.uniform(3.0, 9.5), 1)
        p["bio"] = (
            f"{p['name']} is a {p['age']}-year-old {p['occupation'].lower()} based in "
            f"{p.get('location', 'their city')} who fits the target profile: "
            f"{target_audience.strip()[:120]}."
        )
        behaviors = [_BEHAVIOR_BY_TAG[t] for t in p["tags"] if t in _BEHAVIOR_BY_TAG][:2]
        p["behavioral_pattern"] = (
            f"{p['name']} typically {' and '.join(behaviors)}." if behaviors
            else f"{p['name']} follows a fairly typical adoption process for their role."
        )
        psych = [_PSYCHOLOGY_BY_TAG[t] for t in p["tags"] if t in _PSYCHOLOGY_BY_TAG][:2]
        p["psychological_profile"] = (
            f"At their core, {p['name']} {' and '.join(psych)}." if psych
            else f"{p['name']}'s decisions are mostly driven by practical day-to-day needs."
        )
        p["quote"] = ""
    return roster

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
    """Fully local persona generation — used as the fallback when Groq is
    unavailable. Names/ages/occupations plus randomized traits/scores/bio."""
    roster = random_roster(count)
    return fill_traits_locally(roster, target_audience)


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


def get_persona_response(persona: dict, message: str, history: list[dict], product_name: str = None) -> str:
    """Mocks POST /api/interview/message — a persona's conversational reply.

    Picks a canned response that's topically relevant to the question asked,
    instead of a fully random one, so "how much would you pay" doesn't get
    answered with an unrelated line about existing tools. Weaves in the
    actual product name when known, so it doesn't read as totally generic.
    """
    msg = message.lower()
    p = product_name.strip() if product_name else None
    ref = f" for {p}" if p else ""

    if any(w in msg for w in ["pay", "price", "cost", "$", "afford", "subscription"]):
        return f"Honestly, price matters to me — I'd expect something in the $10-15/month range{ref}."
    if any(w in msg for w in ["concern", "worry", "privacy", "risk", "trust", "data"]):
        return f"That's a good question. My biggest concern{ref} would be data privacy."
    if any(w in msg for w in ["mobile", "daily", "phone", "app", "often", "frequently"]):
        return f"If it worked smoothly on mobile, I'd probably use{' ' + p if p else ' it'} daily."
    if any(w in msg for w in ["compare", "today", "currently", "alternative", "instead", "existing"]):
        return f"I like the idea{ref}, but I'd need to see how it fits with tools I already use."
    if any(w in msg for w in ["feature", "switch", "want", "need", "convince"]):
        return f"As someone balancing a lot day-to-day, I'd want{ref if ref else ' this'} to save me time, not add steps."

    canned = [
        f"As someone balancing a lot day-to-day, I'd want{ref if ref else ' this'} to save me time, not add steps.",
        f"Honestly, price matters to me — I'd expect something in the $10-15/month range{ref}.",
        f"I like the idea{ref}, but I'd need to see how it fits with tools I already use.",
        f"That's a good question. My biggest concern{ref} would be data privacy.",
        f"If it worked smoothly on mobile, I'd probably use{' ' + p if p else ' it'} daily.",
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
