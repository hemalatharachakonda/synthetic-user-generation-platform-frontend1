"""
API client. When BACKEND_BASE_URL is configured, Experiments/Personas/Survey/
Interview/Insights persist to the real backend (database-backed, resumable,
with server-side persona memory across Survey and Interview). Every backend
call falls back automatically to Groq-direct + local mock data on any
failure (unset URL, network error, unexpected response), so the app always
works either way. Every page/component calls functions from here, so no
other file needs to change if this logic changes later.
"""

import json
import random
import uuid
import requests
import streamlit as st
from config import (
    GROQ_TIMEOUT_SECONDS, GROQ_API_KEY, GROQ_MODEL,
    BACKEND_BASE_URL, BACKEND_TIMEOUT_SECONDS,
)
from services import mock_data
from services.data_processor import score_from_answer_text

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


def _backend_get(path: str, params: dict = None):
    """GET against the real backend. Returns parsed JSON, or None on any
    failure (backend not configured, unreachable, non-2xx, bad JSON) so
    every caller can fall back to Groq/local cleanly, the same pattern
    already used for _call_groq below."""
    if not BACKEND_BASE_URL:
        return None
    try:
        resp = requests.get(f"{BACKEND_BASE_URL}{path}", params=params, timeout=BACKEND_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError):
        return None


def _backend_post(path: str, json_body: dict = None):
    """POST against the real backend. Same fallback contract as _backend_get."""
    if not BACKEND_BASE_URL:
        return None
    try:
        resp = requests.post(f"{BACKEND_BASE_URL}{path}", json=json_body, timeout=BACKEND_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError):
        return None


def _backend_put(path: str, json_body: dict = None):
    if not BACKEND_BASE_URL:
        return None
    try:
        resp = requests.put(f"{BACKEND_BASE_URL}{path}", json=json_body, timeout=BACKEND_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError):
        return None


# ── Experiments ───────────────────────────────────────────────────────────────

def create_experiment(product_name, description, target_audience, objectives, persona_count=6) -> dict:
    backend = _backend_post("/api/experiments", {
        "title": product_name,
        "product_description": description,
        "target_audience": target_audience,
        "research_objectives": objectives,
        "persona_count": persona_count,
    })
    if backend and backend.get("id"):
        return {
            "id": backend["id"],
            "product_name": backend.get("title", product_name),
            "description": backend.get("product_description", description),
            "target_audience": backend.get("target_audience", target_audience),
            "objectives": backend.get("research_objectives", objectives),
            "status": backend.get("status", "draft"),
            "_backend": True,
        }

    # Backend unset or unreachable — fully local, same as before.
    return {
        "id": f"exp_{uuid.uuid4().hex[:8]}",
        "product_name": product_name,
        "description": description,
        "target_audience": target_audience,
        "objectives": objectives,
        "status": "draft",
        "_backend": False,
    }


def list_recent_experiments() -> list[dict]:
    """Pulls the recent-experiments list (with status: draft/personas_ready/
    running/completed) from the backend dashboard overview. Returns an empty
    list if no backend is configured or it's unreachable — callers should
    fall back to session-local history (experiments_history) in that case."""
    data = _backend_get("/api/dashboard/overview")
    if not data:
        return []
    return data.get("recent_experiments", [])


def get_experiment(experiment_id: str) -> dict | None:
    """Fetches full experiment details for resuming a previous session."""
    backend = _backend_get(f"/api/experiments/{experiment_id}")
    if not backend:
        return None
    return {
        "id": backend["id"],
        "product_name": backend.get("title", ""),
        "description": backend.get("product_description", ""),
        "target_audience": backend.get("target_audience", ""),
        "objectives": backend.get("research_objectives", ""),
        "status": backend.get("status", "draft"),
        "_backend": True,
    }


def get_personas_for_experiment(experiment_id: str) -> list[dict]:
    """Fetches previously-generated personas for an experiment being
    resumed. Returns an empty list on any failure."""
    backend = _backend_get(f"/api/personas/experiment/{experiment_id}")
    if not backend:
        return []
    return [_map_backend_persona(p) for p in backend.get("items", [])]


def _map_backend_persona(p: dict) -> dict:
    """Maps a backend PersonaResponse into the shape the frontend already
    uses everywhere (id/name/age/occupation/location/tags/adoption_score/
    bio/quote/avatar_seed)."""
    return {
        "id": p["id"],
        "name": p["name"],
        "age": p.get("age"),
        "occupation": p.get("occupation", ""),
        "location": p.get("location", ""),
        "tags": p.get("tags") or p.get("personality_traits", [])[:4],
        "adoption_score": p.get("adoption_score", 5.0),
        "bio": p.get("bio", ""),
        "quote": p.get("quote") or "",
        "avatar_seed": p.get("avatar_seed", p["id"]),
    }


# ── Personas ──────────────────────────────────────────────────────────────────

def _enrich_personas_via_groq(roster: list[dict], product_name: str, description: str,
                               target_audience: str, objectives: str):
    """Given a roster with only name/age/occupation/avatar_seed filled in
    (from local mock pools), asks Groq to generate everything that actually
    requires judgment: personality traits, an adoption score, a bio, and a
    representative quote — grounded in the real product and each specific
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
    if experiment.get("_backend") and experiment.get("id"):
        backend = _backend_post("/api/personas/generate", {
            "experiment_id": experiment["id"],
            "persona_count": count,
        })
        if backend and backend.get("items"):
            return [_map_backend_persona(p) for p in backend["items"]]
        # falls through to Groq/local below on any backend failure

    # Names, ages, occupations always come from local mock pools.
    roster = mock_data.random_roster(count)

    if GROQ_API_KEY:
        enriched = _enrich_personas_via_groq(roster, product_name, description, target_audience, objectives)
        if enriched:
            return enriched
        # falls through to local fallback below on any Groq failure

    return mock_data.fill_traits_locally(roster, target_audience)


# ── Survey ────────────────────────────────────────────────────────────────────

def _run_survey_via_groq(personas: list[dict], question: str) -> dict | None:
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
        "product — treat it as context for their personality, not a cap: a specific "
        "question can reasonably score higher or lower than that baseline if the "
        "question itself points that way (e.g. a price-focused question can score "
        "lower even for an otherwise enthusiastic persona). Just keep the reasoning "
        "believable for who they are — don't flip a skeptic into a superfan for no "
        "reason. Respond with ONLY a JSON array — no "
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


def _run_survey_via_backend(experiment_id: str, question: str) -> dict | None:
    """Creates a one-question survey and executes it immediately, so Survey
    Mode can keep asking one question at a time against a backend built for
    batched multi-question surveys. Returns {persona_id: {score, comment}}
    or None on any failure so the caller can fall back cleanly."""
    created = _backend_post("/api/surveys", {
        "experiment_id": experiment_id,
        "title": question[:190] or "Survey question",
        "questions": [question],
    })
    if not created or not created.get("id"):
        return None

    executed = _backend_post("/api/surveys/execute", {"survey_id": created["id"]})
    if not executed or not executed.get("persona_responses"):
        return None

    results = {}
    for pr in executed["persona_responses"]:
        pid = pr.get("persona_id")
        answers = pr.get("responses") or []
        if not pid or not answers:
            continue
        answer_text = answers[0].get("answer", "")
        rating = answers[0].get("rating")
        if rating is None:
            # backend didn't return a rating for this one (shouldn't normally
            # happen now that his backend supports it) — fall back to the
            # text heuristic rather than showing a blank score.
            rating = score_from_answer_text(answer_text, answers[0].get("confidence", 0.7))
        results[pid] = {
            "score": rating,
            "comment": answer_text,
        }
    return results or None


def run_survey_question(personas: list[dict], question: str) -> dict:
    experiment = st.session_state.get("experiment") or {}
    if experiment.get("_backend") and experiment.get("id"):
        backend_results = _run_survey_via_backend(experiment["id"], question)
        if backend_results:
            missing = [p for p in personas if p["id"] not in backend_results]
            if missing:
                backend_results.update(mock_data.run_survey_question(missing, question))
            return backend_results
        # falls through to Groq/local below on any backend failure

    if GROQ_API_KEY:
        grounded = _run_survey_via_groq(personas, question)
        if grounded:
            # fill in any persona Groq happened to skip using the mock fallback
            missing = [p for p in personas if p["id"] not in grounded]
            if missing:
                grounded.update(mock_data.run_survey_question(missing, question))
            return grounded
        # fall through to mock on any failure so the UI never shows blanks
    return mock_data.run_survey_question(personas, question)


# ── Interview ─────────────────────────────────────────────────────────────────

def _call_groq(messages: list[dict], max_tokens: int = 220) -> str:
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
        return data["choices"][0]["message"]["content"].strip()
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
        "\n\nIMPORTANT — you already answered some survey questions about this product earlier. "
        "Stay consistent with these prior answers; do not contradict them:\n" + "\n".join(lines)
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
        "or mention that you are an AI."
        + _persona_survey_context(persona)
    )


def _get_or_create_interview_session(experiment_id: str, persona_id: str) -> str | None:
    """Finds this persona's existing interview session (so returning to the
    same persona resumes the same conversation instead of starting fresh),
    creating one if none exists yet. Caches the session id in session_state
    to avoid re-querying on every message. Returns None on any failure."""
    cache = st.session_state.setdefault("interview_session_ids", {})
    if persona_id in cache:
        return cache[persona_id]

    existing = _backend_get("/api/interviews", params={"experiment_id": experiment_id, "persona_id": persona_id})
    if existing and existing.get("items"):
        session_id = existing["items"][0]["id"]
        cache[persona_id] = session_id
        return session_id

    created = _backend_post("/api/interviews", {"experiment_id": experiment_id, "persona_id": persona_id})
    if created and created.get("id"):
        cache[persona_id] = created["id"]
        return created["id"]
    return None


def get_interview_history(experiment_id: str, persona_id: str) -> list[dict]:
    """Fetches this persona's persisted conversation so far, to hydrate
    chat_history when (re)opening Interview Mode — including after a
    browser refresh or a brand new session, since it's backend-stored, not
    just kept in st.session_state. Returns [] on any failure (no backend,
    unreachable, or no session exists yet — a fresh conversation)."""
    session_id = _get_or_create_interview_session(experiment_id, persona_id)
    if not session_id:
        return []
    session = _backend_get(f"/api/interviews/{session_id}")
    if not session:
        return []
    return [{"role": m.get("role"), "content": m.get("content")} for m in session.get("messages", [])]


def _get_persona_response_via_backend(experiment_id: str, persona: dict, message: str) -> str | None:
    session_id = _get_or_create_interview_session(experiment_id, persona["id"])
    if not session_id:
        return None
    result = _backend_post(f"/api/interviews/{session_id}/message", {
        "persona_id": persona["id"],
        "message": message,
    })
    if not result or not result.get("messages"):
        return None
    # Last message should be the assistant's reply just generated.
    for msg in reversed(result["messages"]):
        if msg.get("role") == "assistant":
            return msg.get("content")
    return None


def get_persona_response(persona: dict, message: str, history: list[dict]) -> str:
    experiment = st.session_state.get("experiment") or {}
    if experiment.get("_backend") and experiment.get("id"):
        reply = _get_persona_response_via_backend(experiment["id"], persona, message)
        if reply:
            return reply
        # falls through to Groq/local below on any backend failure

    if GROQ_API_KEY:
        messages = [{"role": "system", "content": _persona_system_prompt(persona)}]
        # history already includes the just-sent user message as its last entry
        for turn in history[-10:]:
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
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict) and isinstance(data.get("suggestions"), list):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def extract_insights(personas: list[dict], survey_responses: dict, chat_history: dict) -> dict:
    experiment = st.session_state.get("experiment") or {}
    if experiment.get("_backend") and experiment.get("id"):
        backend = _backend_post(f"/api/insights/generate/{experiment['id']}")
        if backend:
            return {
                "would_use_pct": backend.get("would_use_pct", 0),
                "would_pay_pct": backend.get("would_pay_pct", 0),
                "themes": backend.get("themes", []),
                "sentiment": backend.get("sentiment", {}),
                "key_quotes": backend.get("key_quotes", []),
                "suggestions": backend.get("suggestions", []),
                "user_wants_summary": backend.get("user_wants_summary", ""),
            }
        # falls through to Groq/local below on any backend failure

    # Local path — the base chart data is always built locally, then layered
    # with a real Groq-grounded analysis on top when a key is configured —
    # grounded in the actual product + personas even before any survey/
    # interview exists.
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
            insights["user_wants_summary"] = grounded.get(
                "user_wants_summary", insights.get("user_wants_summary", "")
            )
            insights["suggestions"] = grounded.get("suggestions", insights.get("suggestions", []))

    insights.setdefault("suggestions", [])
    insights.setdefault("user_wants_summary", "")
    return insights


# ── Reports ───────────────────────────────────────────────────────────────────

def generate_report(experiment: dict, personas: list[dict], insights: dict) -> dict:
    # Note: the real backend doesn't have a /reports/generate endpoint yet
    # (Milestone 1 only covers Experiments + Personas), so this is always
    # assembled locally.
    return {
        "experiment": experiment,
        "personas": personas,
        "insights": insights,
    }
