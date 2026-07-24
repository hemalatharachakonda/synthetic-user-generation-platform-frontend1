"""
API client — fully local, no backend server. Experiments/Personas/Survey/
Interview/Insights all run on Groq directly (when GROQ_API_KEY is set),
with automatic fallback to local mock data on any failure, so the app
always works either way. Every page/component calls functions from here,
so no other file needs to change if this logic changes later.

Persona memory & consistency (no ML training involved — this is standard
prompt/context engineering, the same technique used by essentially every
production AI character/persona product):
  - Each persona's fixed attributes (name, age, occupation, location, traits,
    bio) are resent on every single call, so they never drift.
  - Full conversation history is resent every turn within Interview Mode,
    so a persona doesn't contradict what they said 2 questions ago.
  - Interview Mode reads a persona's prior Survey Mode answers, and Survey
    Mode reads a persona's prior Interview Mode answers — consistency flows
    both ways, regardless of which mode was used first.
"""

import json
import random
import uuid
import requests
import streamlit as st
from config import GROQ_TIMEOUT_SECONDS, GROQ_API_KEY, GROQ_MODEL
from services import mock_data

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


# ── Experiments ───────────────────────────────────────────────────────────────

def create_experiment(product_name, description, target_audience, objectives, persona_count=6) -> dict:
    return {
        "id": f"exp_{uuid.uuid4().hex[:8]}",
        "product_name": product_name,
        "description": description,
        "target_audience": target_audience,
        "objectives": objectives,
        "status": "draft",
    }


# ── Personas ──────────────────────────────────────────────────────────────────

def _enrich_personas_via_groq(roster: list[dict], product_name: str, description: str,
                               target_audience: str, objectives: str):
    """Given a roster with only name/occupation/location/avatar_seed filled in
    (from local mock pools), asks Groq to generate everything that actually
    requires judgment: age, personality traits, an adoption score, a bio, and
    a representative quote — grounded in the real product and each specific
    persona. Returns None on any failure so the caller can fall back locally."""
    slim_roster = [{"id": p["id"], "name": p["name"], "occupation": p["occupation"],
                     "location": p.get("location", "")}
                   for p in roster]

    system_prompt = (
        "You are a synthetic user research analyst. You are given a product and a "
        "roster of personas (name, occupation, and location already fixed — do not "
        "change these). For EACH persona, generate a realistic age for that name/occupation/location "
        "and target audience, plus realistic, DIFFERENT personality traits, an "
        "adoption score, a short bio, and a representative quote — grounded in who "
        "they specifically are and how this specific product would land for them. "
        "Personas should genuinely disagree with each other where realistic (some "
        "skeptical, some enthusiastic), not all be uniformly positive. Respond with "
        "ONLY a JSON array — no markdown, no code fences, no commentary — one entry "
        "per persona id given, same order, in exactly this shape:\n"
        '[{"persona_id": "...", "age": 18-75 (fits the occupation and target '
        'audience), "tags": ["3-4 short traits like Early Adopter, '
        'Budget-Conscious, Skeptical, Tech-Savvy"], "adoption_score": 1-10 (one '
        'decimal), "bio": "2-3 sentences, first-person-adjacent, tying their life to '
        'this product", "quote": "one first-person sentence, their honest reaction "'
        'to this specific product"}]'
    )
    user_prompt = (
        f"Product: \"{product_name}\" — {description}\n"
        f"Target audience: {target_audience}\n"
        f"Research objectives: {objectives}\n"
        f"Persona roster: {json.dumps(slim_roster)}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw = _call_groq(messages, max_tokens=1200)
    if not raw:
        return None

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned.split("\n", 1)[-1]
    try:
        data = json.loads(cleaned)
        if not isinstance(data, list):
            return None
    except (json.JSONDecodeError, TypeError):
        return None

    by_id = {entry.get("persona_id"): entry for entry in data if entry.get("persona_id")}
    enriched = []
    for p in roster:
        entry = by_id.get(p["id"])
        if not entry:
            continue  # filled in from the local fallback below instead
        score = entry.get("adoption_score", 5.0)
        try:
            score = round(float(score), 1)
        except (TypeError, ValueError):
            score = 5.0
        age = entry.get("age")
        try:
            age = int(age)
            if not (18 <= age <= 90):
                age = random.randint(22, 58)
        except (TypeError, ValueError):
            age = random.randint(22, 58)
        enriched.append({
            **p,
            "age": age,
            "tags": entry.get("tags") or [],
            "adoption_score": max(1.0, min(10.0, score)),
            "bio": entry.get("bio", ""),
            "quote": entry.get("quote", ""),
        })

    # Any persona Groq happened to skip gets filled in locally, so the roster
    # is always complete even if the model returns fewer entries than asked.
    covered_ids = {p["id"] for p in enriched}
    missing = [p for p in roster if p["id"] not in covered_ids]
    if missing:
        enriched.extend(mock_data.fill_traits_locally(missing, target_audience))

    return enriched


def generate_personas(experiment: dict, product_name, description, target_audience, objectives, count) -> list[dict]:
    # Names, occupations, locations always come from local mock pools.
    roster = mock_data.random_roster(count)

    if GROQ_API_KEY:
        enriched = _enrich_personas_via_groq(roster, product_name, description, target_audience, objectives)
        if enriched:
            return enriched
        # falls through to local fallback below on any Groq failure

    return mock_data.fill_traits_locally(roster, target_audience)


# ── Survey ────────────────────────────────────────────────────────────────────

def _persona_interview_notes(persona_id: str) -> str:
    """Summarizes this persona's prior Interview Mode answers (if any) so
    their Survey Mode answers stay consistent instead of contradicting what
    they already said when interviewed earlier — the mirror of
    _persona_survey_context, which does the same thing in reverse.

    Intentionally uncapped: a persona's memory shouldn't forget anything they
    said more than 3 exchanges ago just because the conversation moved on.
    """
    turns = st.session_state.get("chat_history", {}).get(persona_id) or []
    pairs = []
    pending_question = None
    for turn in turns:
        if turn.get("role") == "user":
            pending_question = turn.get("content")
        elif turn.get("role") == "assistant" and pending_question:
            pairs.append(f'Asked "{pending_question}", answered: "{turn.get("content", "")}"')
            pending_question = None
    return " | ".join(pairs) if pairs else ""


def _persona_prior_survey_notes(persona_id: str, exclude_idx: int | None = None) -> str:
    """Summarizes this SAME persona's answers to any OTHER questions already
    asked earlier in the current survey run, so question 3 doesn't contradict
    question 1 just because each question was being scored independently.
    This is the gap that produces things like an 8.9 adoption score but a
    7/10 answer to a differently-worded 'how likely are you to use this?'
    question — without this, every survey question was answered in total
    isolation from every other survey question."""
    questions = st.session_state.get("survey_questions") or []
    responses = st.session_state.get("survey_responses") or {}
    notes = []
    for q_idx, q_text in enumerate(questions):
        if exclude_idx is not None and q_idx == exclude_idx:
            continue
        answer = (responses.get(q_idx) or {}).get(persona_id)
        if answer:
            notes.append(f'Asked "{q_text}", you rated it {answer.get("score", "-")}/10 '
                         f'and said: "{answer.get("comment", "")}"')
    return " | ".join(notes) if notes else ""


def _run_survey_via_groq(personas: list[dict], question: str, question_idx: int | None = None) -> dict | None:
    """Asks Groq to answer the actual survey question in-character for every
    persona in one batched call. Returns {persona_id: {score, comment}} or
    None on any failure so the caller can fall back to mock data cleanly."""
    experiment = st.session_state.get("experiment") or {}
    roster = [
        {
            "id": p["id"],
            "name": p["name"],
            "age": p.get("age"),
            "occupation": p.get("occupation"),
            "location": p.get("location"),
            "traits": p.get("tags", []),
            "bio": p.get("bio", ""),
            "baseline_adoption_score": p.get("adoption_score"),
            "prior_interview_notes": _persona_interview_notes(p["id"]),
            "prior_survey_notes": _persona_prior_survey_notes(p["id"], exclude_idx=question_idx),
        }
        for p in personas
    ]

    system_prompt = (
        "You are simulating survey responses from multiple distinct personas "
        "reacting to a real product survey question. For EACH persona in the "
        "roster, answer fully in character based on their age, occupation, "
        "location, traits, and bio — different personas should give genuinely "
        "different answers, not near-identical ones. Each persona also has a "
        "baseline_adoption_score reflecting their general attitude toward this "
        "product. Treat that score as their settled, memorized opinion, not a "
        "fresh dice roll: if this question is essentially asking the same thing "
        "as 'how likely are you to use/adopt this product' (just reworded), your "
        "score MUST land within 1 point of baseline_adoption_score — do not "
        "silently redecide their overall attitude every time the same question is "
        "reworded. A more specific, narrower question (e.g. about price, a single "
        "feature, or a specific worry) CAN reasonably score higher or lower than "
        "that baseline, because it's measuring something more specific than 'would "
        "you use this overall' — but the reasoning must stay believable for who "
        "this persona is; don't flip a skeptic into a superfan for no reason. Every "
        "persona has a persistent memory of this whole research session: if "
        "prior_interview_notes or prior_survey_notes is non-empty, you MUST stay "
        "consistent with what they already said there — do not contradict it, and "
        "where relevant, build on it (e.g. repeat/refine a suggestion they already "
        "raised rather than inventing an unrelated new one). Every persona's "
        "\"comment\" must be written in English, regardless of the persona's "
        "location or background — this is an English-language research report. "
        "Respond with ONLY a JSON array — no "
        "markdown, no code fences, no commentary — in exactly this shape, one "
        "entry per persona id given, same order:\n"
        '[{"persona_id": "...", "score": 1-10 (how positively they answer / '
        'likelihood to adopt), "comment": "one short first-person sentence, '
        'their actual voice, directly answering the question"}]'
    )
    user_prompt = (
        f"Product: \"{experiment.get('product_name', 'this product')}\" — "
        f"{experiment.get('description', '')}\n"
        f"Target audience: {experiment.get('target_audience', 'not specified')}\n"
        f"Survey question: \"{question}\"\n"
        f"Persona roster: {json.dumps(roster)}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw = _call_groq(messages, max_tokens=900)
    if not raw:
        return None

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned.split("\n", 1)[-1]
    try:
        data = json.loads(cleaned)
        if not isinstance(data, list):
            return None
        results = {}
        for entry in data:
            pid = entry.get("persona_id")
            if not pid:
                continue
            score = entry.get("score")
            try:
                score = max(1, min(10, int(score)))
            except (TypeError, ValueError):
                score = 5
            results[pid] = {"score": score, "comment": entry.get("comment", "")}
        # make sure every persona got an answer; anything missing falls back below
        if all(p["id"] in results for p in personas):
            return results
        return results or None
    except (json.JSONDecodeError, TypeError):
        return None


_ADOPTION_QUESTION_KEYWORDS = (
    "likely are you to use", "likely would you use", "would you use this",
    "would you buy", "would you adopt", "would you recommend",
    "how likely are you", "chances you'd use", "likelihood",
)


def _is_primary_adoption_question(question: str) -> bool:
    """Heuristic for detecting when a survey question is just a reworded version
    of 'how likely are you to use/adopt this product overall' — i.e. the same
    thing the persona's adoption_score already represents. Used to keep the
    adoption score shown in the Persona Gallery / Interview badge from silently
    drifting away from what Survey Mode just measured for that same question."""
    q = (question or "").lower()
    return any(kw in q for kw in _ADOPTION_QUESTION_KEYWORDS)


def _sync_adoption_scores(personas: list[dict], question: str, results: dict) -> None:
    """When the survey question just asked is essentially the persona's overall
    adoption question, updates each persona's stored adoption_score to match
    the measured answer. This is what keeps the score shown on the Persona
    Gallery / Interview badge in sync with what Survey Mode actually measured,
    instead of showing two different numbers (e.g. 8.9 at creation time vs 7
    from a later, differently-worded survey question) for the same question."""
    if not _is_primary_adoption_question(question):
        return
    roster = st.session_state.get("personas") or []
    by_id = {p["id"]: p for p in roster}
    for p in personas:
        answer = results.get(p["id"])
        if not answer:
            continue
        score = answer.get("score")
        if score is None:
            continue
        live = by_id.get(p["id"])
        if live is not None:
            live["adoption_score"] = round(float(score), 1)


def run_survey_question(personas: list[dict], question: str, question_idx: int | None = None) -> dict:
    if GROQ_API_KEY:
        grounded = _run_survey_via_groq(personas, question, question_idx)
        if grounded:
            # fill in any persona Groq happened to skip using the mock fallback
            missing = [p for p in personas if p["id"] not in grounded]
            if missing:
                grounded.update(mock_data.run_survey_question(missing, question))
            _sync_adoption_scores(personas, question, grounded)
            return grounded
        # fall through to mock on any failure so the UI never shows blanks
    results = mock_data.run_survey_question(personas, question)
    _sync_adoption_scores(personas, question, results)
    return results


# ── Interview ─────────────────────────────────────────────────────────────────

def _looks_incomplete(text: str) -> bool:
    """Rough heuristic for a response that got cut off mid-thought (e.g. an API
    hiccup or hitting max_tokens before finishing a sentence) — like literally
    "I gave it a" and nothing else. Not perfect, but catches the obvious cases
    so we can retry once instead of showing a broken half-sentence."""
    t = (text or "").strip()
    if len(t) < 15:
        return True
    if t[-1] not in ".!?\u2019\u201d\"'":
        return True
    return False


def _call_groq(messages: list[dict], max_tokens: int = 220, _retry: bool = True) -> str:
    """Direct call to Groq's OpenAI-compatible chat completions endpoint.

    Used for interview responses so personas feel like a real (simulated)
    person reacting to the actual question, instead of a canned line.
    """
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.8,
    }
    try:
        resp = requests.post(GROQ_CHAT_URL, headers=headers, json=payload, timeout=GROQ_TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
        reply = data["choices"][0]["message"]["content"].strip()
        finish_reason = data["choices"][0].get("finish_reason")
        # If the model got cut off before finishing a thought, retry once with
        # more room instead of showing a half sentence like "I gave it a".
        if _retry and (finish_reason == "length" or _looks_incomplete(reply)):
            return _call_groq(messages, max_tokens=max_tokens + 200, _retry=False) or reply
        return reply
    except requests.RequestException as e:
        st.error(f"Groq request failed: {e}")
        return ""
    except (KeyError, IndexError):
        st.error("Unexpected response format from Groq.")
        return ""


def _persona_survey_context(persona: dict) -> str:
    """Pulls this persona's own prior Survey Mode answers (if any) so their
    Interview Mode opinions stay consistent instead of contradicting what
    they already said when asked the same kind of question earlier."""
    questions = st.session_state.get("survey_questions") or []
    responses = st.session_state.get("survey_responses") or {}
    pid = persona["id"]

    lines = []
    for q_idx, q_text in enumerate(questions):
        answer = (responses.get(q_idx) or {}).get(pid)
        if answer:
            lines.append(f'- Asked "{q_text}", you rated it {answer.get("score", "-")}/10 '
                         f'and said: "{answer.get("comment", "")}"')

    if not lines:
        return ""
    return (
        "\n\nIMPORTANT — this is your persistent memory of this research session. You already "
        "answered these survey questions about this product earlier. Stay fully consistent with "
        "these prior answers: don't contradict them, and if you raised a suggestion or concern "
        "before, build on it here instead of inventing an unrelated new one:\n" + "\n".join(lines)
    )


def _persona_system_prompt(persona: dict) -> str:
    experiment = st.session_state.get("experiment") or {}
    return (
        f"You are role-playing as {persona['name']}, a {persona['age']}-year-old "
        f"{persona['occupation']} based in {persona.get('location', 'an unspecified city')}. "
        f"Personality traits: {', '.join(persona.get('tags', []))}. "
        f"Background: {persona.get('bio', '')} "
        f"Your general attitude toward this product is a "
        f"{persona.get('adoption_score', '?')}/10 likelihood to adopt it — treat that as "
        f"context for your personality and priorities, not a script: a specific question "
        f"(e.g. about price, or a specific worry) can reasonably pull your answer more "
        f"positive or negative than that number, as long as it's believable for who you are. "
        f"You are being interviewed as a potential user of a product called "
        f"\"{experiment.get('product_name', 'this product')}\": "
        f"{experiment.get('description', 'No description provided.')} "
        f"Target audience it's built for: {experiment.get('target_audience', 'not specified')}. "
        "Answer the interviewer's questions fully in character, in first person. "
        "Keep answers conversational and concise (2-4 sentences), grounded in your "
        "persona's life, priorities, and personality — not generic marketing-speak. "
        "Give honest, specific opinions: if skeptical, say so and why; if enthusiastic, "
        "say so and why. Directly address what was actually asked. Never break character "
        "or mention that you are an AI. Always respond in English — regardless of your "
        "persona's location or background, this research is being read by an English-"
        "speaking product team, so answer in English even if you'd naturally code-switch "
        "in real life."
        + _persona_survey_context(persona)
    )


def get_persona_response(persona: dict, message: str, history: list[dict]) -> str:
    experiment = st.session_state.get("experiment") or {}
    if GROQ_API_KEY:
        messages = [{"role": "system", "content": _persona_system_prompt(persona)}]
        # history already includes the just-sent user message as its last entry.
        # Capped generously (not to 3-4 turns) so the persona doesn't "forget"
        # something they said earlier in a long interview and contradict it later.
        for turn in history[-30:]:
            role = "assistant" if turn["role"] == "assistant" else "user"
            messages.append({"role": role, "content": turn["content"]})
        reply = _call_groq(messages)
        if reply:
            return reply
        # fall through to mock on any failure so the UI never shows a blank response
    return mock_data.get_persona_response(persona, message, history, product_name=experiment.get("product_name"))


# ── Insights ──────────────────────────────────────────────────────────────────

def _build_feedback_transcript(personas: list[dict], survey_responses: dict, chat_history: dict) -> str:
    """Flattens persona profiles plus any actual survey comments + interview
    replies into one text block, so insights are always grounded in the real
    product and personas — richer still when real survey/interview data exists."""
    id_to_name = {p["id"]: p["name"] for p in personas}
    lines = ["Persona roster:"]
    for p in personas:
        lines.append(
            f"- {p['name']} ({p.get('age','?')}, {p.get('occupation','')}) — "
            f"traits: {', '.join(p.get('tags', []))}; adoption score: {p.get('adoption_score','?')}/10; "
            f"bio: {p.get('bio','')}"
        )

    feedback_lines = []
    for q_idx, responses in (survey_responses or {}).items():
        for pid, r in (responses or {}).items():
            name = id_to_name.get(pid, pid)
            feedback_lines.append(f"[Survey] {name} (score {r.get('score')}): {r.get('comment')}")
    for pid, turns in (chat_history or {}).items():
        name = id_to_name.get(pid, pid)
        for turn in turns or []:
            if turn.get("role") == "user":
                continue
            feedback_lines.append(f"[Interview] {name}: {turn.get('content', '')}")

    if feedback_lines:
        lines.append("\nActual survey/interview feedback:")
        lines.extend(feedback_lines)

    return "\n".join(lines)[:6000]


def _extract_suggestions_via_groq(personas: list[dict], survey_responses: dict, chat_history: dict):
    """Asks Groq for a full insights payload — themes, sentiment, attributed
    quotes, suggestions, and a summary — grounded in the real product and
    persona roster (plus real survey/interview feedback when it exists).
    Returns None on any failure so callers can fall back to mock data cleanly."""
    experiment = st.session_state.get("experiment") or {}
    transcript = _build_feedback_transcript(personas, survey_responses, chat_history)
    has_real_feedback = bool(survey_responses or chat_history)

    system_prompt = (
        "You are a product research analyst. Below is a product description and "
        "a roster of synthetic user personas being tested against it"
        + (", plus real feedback they gave in surveys/interviews" if has_real_feedback else
           " (no survey/interview has been run yet — infer plausible reactions strictly "
           "from each persona's own traits, bio, and adoption score, staying true to who "
           "they are, not generic filler)")
        + ". Respond with ONLY a JSON object — no markdown, no code fences, no commentary "
        "— in exactly this shape:\n"
        '{"themes": [{"theme": "short label", "mentions_pct": 20-50}] (3-4 items, '
        'grounded in this specific product and these personas\' actual pain points/motivations), '
        '"sentiment": {"Positive": pct, "Neutral": pct, "Negative": pct} (must sum to 100), '
        '"key_quotes": [{"quote": "one first-person sentence in that persona\'s voice, '
        'about this specific product", "persona": "exact persona name from the roster"}] '
        "(2-3 items, using different personas, quotes must reference the actual product not "
        'generic software), "user_wants_summary": "2-3 plain-English sentences summarizing '
        'what these users want from THIS product", "suggestions": [{"suggestion": '
        '"specific actionable improvement to THIS product", "category": "short label like '
        'Pricing, Feature, UX, Trust, Support, Performance, Design", "priority": '
        '"high|medium|low", "personas": ["names who would raise it"]}] (4-6 items, most '
        "important first)}\n"
        "Every theme, quote, and suggestion must be specific to this product and these "
        "personas — never generic placeholder feedback that could apply to any app."
    )
    user_prompt = (
        f"Product: \"{experiment.get('product_name', 'this product')}\" — "
        f"{experiment.get('description', '')}\n"
        f"Target audience: {experiment.get('target_audience', 'not specified')}\n\n"
        f"{transcript}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw = _call_groq(messages, max_tokens=1000)
    if not raw:
        return None

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned.split("\n", 1)[-1]

    def _try_parse(text: str):
        try:
            data = json.loads(text)
            if isinstance(data, dict) and isinstance(data.get("suggestions"), list):
                return data
        except (json.JSONDecodeError, TypeError):
            return None
        return None

    result = _try_parse(cleaned)
    if result:
        return result

    # Fallback: the model may have added stray prose around the JSON despite
    # instructions — try extracting just the {...} substring instead of
    # giving up entirely.
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        result = _try_parse(cleaned[start:end + 1])
        if result:
            return result

    st.warning("Groq returned insights in an unexpected format — showing baseline data instead. Try Recalculate Insights again.")
    return None


def extract_insights(personas: list[dict], survey_responses: dict, chat_history: dict) -> dict:
    # Base chart data is always built locally, then layered with a real
    # Groq-grounded analysis on top when a key is configured — grounded in
    # the actual product + personas even before any survey/interview exists.
    insights = mock_data.extract_insights(personas, survey_responses, chat_history)

    if GROQ_API_KEY and personas:
        grounded = _extract_suggestions_via_groq(personas, survey_responses, chat_history)
        if grounded:
            if grounded.get("themes"):
                insights["themes"] = grounded["themes"]
            if grounded.get("sentiment"):
                insights["sentiment"] = grounded["sentiment"]
            if grounded.get("key_quotes"):
                insights["key_quotes"] = grounded["key_quotes"]
            if grounded.get("user_wants_summary"):
                insights["user_wants_summary"] = grounded["user_wants_summary"]
            if grounded.get("suggestions"):
                insights["suggestions"] = grounded["suggestions"]

    insights.setdefault("suggestions", [])
    insights.setdefault("user_wants_summary", "")
    return insights


# ── Reports ───────────────────────────────────────────────────────────────────

def generate_report(experiment: dict, personas: list[dict], insights: dict) -> dict:
    return {
        "experiment": experiment,
        "personas": personas,
        "insights": insights,
    }
