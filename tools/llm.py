"""
tools/llm.py — LLM broker tool for the resource-aware agent.

Exposes: complete(prompt, **params) -> str
Registered with ToolRegistry the same way as any other tool
(echo, add, get_time, fail_test) — no special-case call path elsewhere
in the agent.

Provider order: Groq (primary) -> Gemini (fallback), each with its own
retry/backoff before the broker gives up on it and moves on.
"""

import os
import time
import random
import logging

import requests

logger = logging.getLogger("agent.llm")

# ---------------------------------------------------------------------------
# Config — read once at import time. A missing key just disables that
# provider (it's skipped, not a crash) so the agent still runs with only
# one provider configured.
# ---------------------------------------------------------------------------

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

MAX_RETRIES = 3
BASE_DELAY = 1.0       # seconds, doubles each retry
REQUEST_TIMEOUT = 30   # seconds


class LLMError(Exception):
    """Raised when every configured provider has failed."""


class ProviderError(Exception):
    """Internal: a single provider call failed. Caught by the retry loop."""


def _retry(fn, *args, **kwargs):
    """Exponential backoff + jitter around a single provider call."""
    last_exc = None
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except ProviderError as e:
            last_exc = e
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt) + random.uniform(0, 0.5)
                logger.warning(
                    "%s attempt %d/%d failed: %s — retrying in %.1fs",
                    fn.__name__, attempt + 1, MAX_RETRIES, e, delay,
                )
                time.sleep(delay)
    raise last_exc


def _call_groq(prompt: str) -> str:
    if not GROQ_API_KEY:
        raise ProviderError("GROQ_API_KEY not set")
    try:
        resp = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        raise ProviderError(f"Groq request failed: {e}")

    if resp.status_code == 429:
        raise ProviderError("Groq rate limited (429)")
    if resp.status_code >= 500:
        raise ProviderError(f"Groq server error ({resp.status_code})")
    if resp.status_code != 200:
        raise ProviderError(f"Groq error {resp.status_code}: {resp.text[:200]}")

    try:
        return resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as e:
        raise ProviderError(f"Unexpected Groq response shape: {e}")


def _call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise ProviderError("GEMINI_API_KEY not set")
    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as e:
        raise ProviderError(f"Gemini request failed: {e}")

    if resp.status_code == 429:
        raise ProviderError("Gemini rate limited (429)")
    if resp.status_code >= 500:
        raise ProviderError(f"Gemini server error ({resp.status_code})")
    if resp.status_code != 200:
        raise ProviderError(f"Gemini error {resp.status_code}: {resp.text[:200]}")

    try:
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, ValueError) as e:
        raise ProviderError(f"Unexpected Gemini response shape: {e}")


def complete(prompt: str, **params) -> str:
    """
    llm.complete(prompt) -> text

    Tries Groq first (with retry/backoff), falls back to Gemini
    (also with retry/backoff) if Groq is exhausted. Raises LLMError
    only if both providers fail.

    Accepts and ignores extra **params so this can be registered
    directly as a ToolRegistry tool — Executor calls tools with
    **params from the Task, same as echo/add/get_time.
    """
    if not prompt or not isinstance(prompt, str):
        raise LLMError("prompt must be a non-empty string")

    errors = []

    try:
        text = _retry(_call_groq, prompt)
        logger.info("llm.complete served by Groq")
        return text
    except ProviderError as e:
        errors.append(f"Groq: {e}")
        logger.warning("Groq exhausted, falling back to Gemini: %s", e)

    try:
        text = _retry(_call_gemini, prompt)
        logger.info("llm.complete served by Gemini (fallback)")
        return text
    except ProviderError as e:
        errors.append(f"Gemini: {e}")

    raise LLMError("All providers failed — " + "; ".join(errors))


def register(registry):
    """
    Register this tool the same way echo/add/get_time/fail_test are
    registered. Call this once from agent.py during startup:

        from tools import llm
        llm.register(tool_registry)
    """
    registry.register("llm_complete", complete)
