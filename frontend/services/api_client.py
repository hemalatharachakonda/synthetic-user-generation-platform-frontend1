"""
API client — the ONLY file that needs to know whether we're using mock data
or your real backend. Every page/component calls functions from here.

TO GO LIVE:
  1. In config.py set USE_MOCK_DATA = False and BACKEND_BASE_URL to your server.
  2. Make sure your backend exposes the endpoints listed below (paths match the
     spec doc: POST /api/personas/generate, POST /api/survey/run, etc).
  3. Nothing else changes — pages import these same function names.
"""

import json
import requests
import streamlit as st
from config import USE_MOCK_DATA, BACKEND_BASE_URL, API_TIMEOUT_SECONDS, GROQ_API_KEY, GROQ_MODEL
from services import mock_data

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


def _post(path: str, payload: dict) -> dict:
    url = f"{BACKEND_BASE_URL}{path}"
    try:
        resp = requests.post(url, json=payload, timeout=API_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        detail = ""
        try:
            detail = f" — {e.response.json()}"
        except Exception:
            detail = f" — {e.response.text[:300]}" if e.response is not None else ""
        st.error(f"Backend request failed ({url}): {e}{detail}")
        return {}
    except requests.RequestException as e:
        st.error(f"Backend request failed ({url}): {e}")
        return {}


def _get(path: str) -> dict:
    url = f"{BACKEND_BASE_URL}{path}"
    try:
        resp = requests.get(url, timeout=API_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as e:
        detail = ""
        try:
            detail = f" — {e.response.json()}"
        except Exception:
            detail = f" — {e.response.text[:300]}" if e.response is not None else ""
        st.error(f"Backend request failed ({url}): {e}{detail}")
        return {}
    except requests.RequestException as e:
        st.error(f"Backend request failed ({url}): {e}")
        return {}


def _dig(d: dict, *paths, default=None):
    """Tries several dotted key-paths against a dict (handles backends that
    nest fields under demographic/behavioral/psychological sub-objects, or
    that use different naming than our mock data)."""
    for path in paths:
        cur = d
        ok = True
        for key in path.split("."):
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok and cur not in (None, ""):
            return cur
    return default


def _normalize_persona(raw: dict) -> dict:
    """Maps a real-backend persona object (whatever shape it comes in) into
    the flat shape every page/component in this app expects. Missing fields
    degrade gracefully instead of raising, so one field mismatch doesn't take
    down the whole gallery."""
    tags = _dig(raw, "tags", "behavioral.personality_traits", "personality_traits", default=[])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    return {
        "id": _dig(raw, "id", "_id", "persona_id", "persona_hash", default=""),
        "name": _dig(raw, "name", "demographic.name", default="Unnamed Persona"),
        "age": _dig(raw, "age", "demographic.age", default=None),
        "occupation": _dig(raw, "occupation", "demographic.occupation", default=""),
        "tags": tags or [],
        "adoption_score": _dig(
            raw, "adoption_score", "product_fit_score", "fit_score", default=5.0
        ),
        "avatar_seed": _dig(raw, "avatar_seed", "id", "_id", default="persona"),
        "bio": _dig(raw, "bio", "narrative.bio", default=""),
        "quote": _dig(raw, "quote", "narrative.quote", default=""),
    }


# ── Experiments ───────────────────────────────────────────────────────────────

def create_experiment(product_name, description, target_audience, objectives) -> dict:
    if USE_MOCK_DATA:
        return {
            "id": f"exp_{abs(hash(product_name)) % 100000}",
            "product_name": product_name,
            "description": description,
            "target_audience": target_audience,
            "objectives": objectives,
            "status": "draft",
        }
    result = _post("/experiments", {
        "product_name": product_name,
        "description": description,
        "target_audience": target_audience,
        "objectives": objectives,
    })
    if not result:
        return {}
    exp_id = _dig(result, "id", "_id", "experiment_id", default="")
    return {
        "id": exp_id,
        "product_name": product_name,
        "description": description,
        "target_audience": target_audience,
        "objectives": objectives,
        "status": result.get("status", "draft"),
    }


# ── Personas ──────────────────────────────────────────────────────────────────

def generate_personas(product_name, description, target_audience, objectives, count) -> list[dict]:
    if USE_MOCK_DATA:
        return mock_data.generate_personas(product_name, description, target_audience, objectives, count)

    experiment = st.session_state.get("experiment") or {}
    exp_id = experiment.get("id")
    if not exp_id:
        # Personas are nested under an experiment on the real backend — create
        # one first if the workspace hasn't already stored an id from create_experiment().
        created = create_experiment(product_name, description, target_audience, objectives)
        exp_id = created.get("id")
        if created:
            st.session_state.experiment = created
    if not exp_id:
        st.error("Could not create an experiment on the backend — check the error above.")
        return []

    gen_result = _post(f"/experiments/{exp_id}/personas/generate", {"persona_count": count})
    if gen_result is None:
        return []

    # Some backends return the personas directly from the generate call;
    # others expect a follow-up GET. Try both.
    raw_list = gen_result.get("personas") if isinstance(gen_result, dict) else None
    if not raw_list:
        fetched = _get(f"/experiments/{exp_id}/personas")
        raw_list = fetched.get("personas", fetched if isinstance(fetched, list) else [])

    return [_normalize_persona(p) for p in (raw_list or [])]


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
            "traits": p.get("tags", []),
            "bio": p.get("bio", ""),
        }
        for p in personas
    ]

    system_prompt = (
        "You are simulating survey responses from multiple distinct personas "
        "reacting to a real product survey question. For EACH persona in the "
        "roster, answer fully in character based on their age, occupation, "
        "traits, and bio — different personas should give genuinely different "
        "answers, not near-identical ones. Respond with ONLY a JSON array — no "
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


def run_survey_question(personas: list[dict], question: str) -> dict:
    if GROQ_API_KEY:
        grounded = _run_survey_via_groq(personas, question)
        if grounded:
            # fill in any persona Groq happened to skip using the mock fallback
            missing = [p for p in personas if p["id"] not in grounded]
            if missing:
                grounded.update(mock_data.run_survey_question(missing, question))
            return grounded
        # fall through to mock on any failure so the UI never shows blanks
    if USE_MOCK_DATA:
        return mock_data.run_survey_question(personas, question)
    result = _post("/survey/run", {
        "persona_ids": [p["id"] for p in personas],
        "question": question,
    })
    return result.get("responses", {})


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
        resp = requests.post(GROQ_CHAT_URL, headers=headers, json=payload, timeout=API_TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.RequestException as e:
        st.error(f"Groq request failed: {e}")
        return ""
    except (KeyError, IndexError):
        st.error("Unexpected response format from Groq.")
        return ""


def _persona_system_prompt(persona: dict) -> str:
    experiment = st.session_state.get("experiment") or {}
    return (
        f"You are role-playing as {persona['name']}, a {persona['age']}-year-old "
        f"{persona['occupation']}. Personality traits: {', '.join(persona.get('tags', []))}. "
        f"Background: {persona.get('bio', '')} "
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
    )


def get_persona_response(persona: dict, message: str, history: list[dict]) -> str:
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
    if USE_MOCK_DATA:
        return mock_data.get_persona_response(persona, message, history)
    result = _post("/interview/message", {
        "persona_id": persona["id"],
        "message": message,
        "history": history,
    })
    return result.get("response", "")


# ── Insights ──────────────────────────────────────────────────────────────────

def _build_feedback_transcript(personas: list[dict], survey_responses: dict, chat_history: dict) -> str:
    """Flattens actual survey comments + interview replies into one text block
    so the "what users want" analysis is grounded in real feedback, not guesses."""
    id_to_name = {p["id"]: p["name"] for p in personas}
    lines = []
    for q_idx, responses in (survey_responses or {}).items():
        for pid, r in (responses or {}).items():
            name = id_to_name.get(pid, pid)
            lines.append(f"[Survey] {name} (score {r.get('score')}): {r.get('comment')}")
    for pid, turns in (chat_history or {}).items():
        name = id_to_name.get(pid, pid)
        for turn in turns or []:
            if turn.get("role") == "user":
                continue
            lines.append(f"[Interview] {name}: {turn.get('content', '')}")
    return "\n".join(lines)[:6000]


def _extract_suggestions_via_groq(personas: list[dict], survey_responses: dict, chat_history: dict):
    """Asks Groq to read the real feedback transcript and return a grounded summary
    of what users want plus concrete, prioritized suggestions. Returns None on any
    failure so callers can fall back cleanly to the mock/heuristic version."""
    transcript = _build_feedback_transcript(personas, survey_responses, chat_history)
    if not transcript.strip():
        return None

    system_prompt = (
        "You are a product research analyst reviewing raw feedback from simulated "
        "user interviews and surveys. Respond with ONLY a JSON object — no markdown, "
        "no code fences, no commentary before or after — in exactly this shape:\n"
        '{"user_wants_summary": "2-3 plain-English sentences summarizing what users '
        'want overall", "suggestions": [{"suggestion": "specific actionable improvement", '
        '"category": "short label like Pricing, Feature, UX, Trust, Support, Performance, Design", '
        '"priority": "high|medium|low", "personas": ["names who raised it"]}]}\n'
        "Base every suggestion strictly on what the transcript actually says — do not "
        "invent feedback. Return 4 to 6 suggestions, most important first."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Feedback transcript:\n{transcript}"},
    ]
    raw = _call_groq(messages, max_tokens=700)
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
    # Note: the real backend doesn't have an /insights/extract endpoint yet
    # (Milestone 1 only covers Experiments + Personas), so this always builds
    # the base chart data locally regardless of USE_MOCK_DATA, and layers a
    # real Groq-grounded summary on top when a key is configured.
    insights = mock_data.extract_insights(personas, survey_responses, chat_history)

    if GROQ_API_KEY and (chat_history or survey_responses):
        grounded = _extract_suggestions_via_groq(personas, survey_responses, chat_history)
        if grounded:
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
    # assembled locally regardless of USE_MOCK_DATA.
    return {
        "experiment": experiment,
        "personas": personas,
        "insights": insights,
    }
