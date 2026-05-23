"""
content_service.py — AI-powered study content generation via local Ollama.

• LLM     : Mistral (or any model pulled into Ollama)
• Endpoint: http://localhost:11434/api/generate  (streaming=False)
• Language: Automatically Uzbek or Russian based on content; prompts are bilingual.
• No external API keys — fully local.

Public surface:
    generate_summary(subject, topic, materials) → str
    generate_tests(subject, topic, materials, count=5) → list[TestQuestion]
"""
from __future__ import annotations

import json
import re
import textwrap
from dataclasses import dataclass, field
from typing import Any

import httpx
from loguru import logger

from services.rag_service import RetrievedChunk

# ─── Ollama settings ──────────────────────────────────────────────────────────

_OLLAMA_URL    = "http://localhost:11434/api/generate"
_DEFAULT_MODEL = "mistral"
_TIMEOUT       = httpx.Timeout(120.0)          # generation can be slow on CPU

# Maximum characters of retrieved context passed to the LLM
_MAX_CONTEXT_CHARS = 4_000
_MAX_SUMMARY_WORDS = 500


# ─── Data types ───────────────────────────────────────────────────────────────

@dataclass(slots=True)
class TestQuestion:
    question:       str
    options:        list[str]          # exactly 4 items: ["A) ...", "B) ...", ...]
    correct_answer: str                # "A", "B", "C", or "D"
    explanation:    str


@dataclass(slots=True)
class GenerationResult:
    subject:    str
    topic:      str
    model_used: str
    content:    str                    # raw LLM output (for summary)


# ─── Ollama client ────────────────────────────────────────────────────────────

async def _ollama_generate(
    prompt: str,
    model: str = _DEFAULT_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 1024,
) -> str:
    """
    Call the local Ollama /api/generate endpoint (non-streaming).

    Raises:
        OllamaUnavailableError — if Ollama is not running.
        OllamaModelError       — if the model is not pulled.
    """
    payload: dict[str, Any] = {
        "model":  model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature":   temperature,
            "num_predict":   max_tokens,
            "top_p":         0.9,
            "repeat_penalty": 1.1,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(_OLLAMA_URL, json=payload)

            if response.status_code == 404:
                body = response.text
                if "model" in body.lower():
                    raise OllamaModelError(
                        f"Model '{model}' is not available. "
                        f"Run: ollama pull {model}"
                    )

            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()

    except httpx.ConnectError as exc:
        raise OllamaUnavailableError(
            "Ollama is not running. Start it with: ollama serve"
        ) from exc
    except httpx.TimeoutException as exc:
        raise OllamaUnavailableError(
            f"Ollama timed out after {_TIMEOUT.read}s — the model may be too large for your CPU."
        ) from exc


# ─── Context builder ─────────────────────────────────────────────────────────

def _build_context(materials: list[RetrievedChunk] | list[str]) -> str:
    """Concatenate retrieved chunks into a single context string, capped at _MAX_CONTEXT_CHARS."""
    parts: list[str] = []
    total = 0
    for item in materials:
        text = item.text if isinstance(item, RetrievedChunk) else str(item)
        if total + len(text) > _MAX_CONTEXT_CHARS:
            remaining = _MAX_CONTEXT_CHARS - total
            if remaining > 100:
                parts.append(text[:remaining])
            break
        parts.append(text)
        total += len(text)
    return "\n\n---\n\n".join(parts)


# ─── 1. Summary generation ────────────────────────────────────────────────────

_SUMMARY_PROMPT = textwrap.dedent("""
    Sen talabalar uchun o'quv materiallarini tayyorlayotgan tajribali o'qituvchisan.
    Quyidagi materiallar asosida "{subject}" fanidan "{topic}" mavzusida
    aniq va tushunarli xulosa yoz.

    Talablar:
    - Maksimal {max_words} so'z
    - Asosiy tushunchalarni ajratib ko'rsat
    - Misollar keltir (agar iloji bo'lsa)
    - O'zbek yoki rus tilida yoz (material tiliga qarab)
    - Markdown formatlashdan foydalanma

    Manba materiallar:
    {context}

    Xulosa:
""").strip()


async def generate_summary(
    subject: str,
    topic: str,
    materials: list[RetrievedChunk] | list[str],
    model: str = _DEFAULT_MODEL,
    max_words: int = _MAX_SUMMARY_WORDS,
) -> str:
    """
    Generate a concise study summary in Uzbek or Russian.

    Args:
        subject   : Subject name, e.g. "Fizika"
        topic     : Topic name, e.g. "Termodinamika"
        materials : Retrieved RAG chunks or plain text strings.
        model     : Ollama model name (default: mistral).
        max_words : Target word limit for the output.

    Returns:
        Generated summary string.

    Raises:
        OllamaUnavailableError if Ollama is not running.
        OllamaModelError if the model is not pulled.
        ContentGenerationError on empty output.
    """
    if not materials:
        raise ContentGenerationError("No materials provided for summary generation.")

    context = _build_context(materials)
    prompt  = _SUMMARY_PROMPT.format(
        subject=subject,
        topic=topic,
        max_words=max_words,
        context=context,
    )

    logger.info("Generating summary: subject='{}' topic='{}' model='{}'", subject, topic, model)
    raw = await _ollama_generate(prompt, model=model, temperature=0.3, max_tokens=max_words * 6)

    if not raw:
        raise ContentGenerationError("Ollama returned an empty summary.")

    # Trim to max_words as a safety net
    words = raw.split()
    if len(words) > max_words:
        raw = " ".join(words[:max_words]) + "…"

    logger.debug("Summary generated: {} words", len(raw.split()))
    return raw


# ─── 2. Test generation ───────────────────────────────────────────────────────

_TEST_PROMPT = textwrap.dedent("""
    Sen talabalar uchun test savollari tuzayotgan o'qituvchisan.
    "{subject}" fanidan "{topic}" mavzusida quyidagi materiallar asosida
    {count} ta test savoli tuz.

    HAR BIR SAVOL UCHUN QOIDALAR:
    - 4 ta variant bo'lsin: A, B, C, D
    - Faqat 1 ta to'g'ri javob bo'lsin
    - Variantlar aniq va adashtiruvchi bo'lsin (lekin to'g'ri javob baholanishi mumkin bo'lsin)
    - Qisqa tushuntirish qo'sh

    JAVOB FORMATI — faqat sof JSON array, boshqa matn yo'q:
    [
      {{
        "question": "Savol matni?",
        "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
        "correct_answer": "A",
        "explanation": "Tushuntirish matni"
      }}
    ]

    Manba materiallar:
    {context}

    JSON:
""").strip()

# Regex to extract the JSON array even if Ollama wraps it in markdown fences
_JSON_ARRAY_RE = re.compile(r"\[\s*\{.*?\}\s*\]", re.DOTALL)


async def generate_tests(
    subject: str,
    topic: str,
    materials: list[RetrievedChunk] | list[str],
    count: int = 5,
    model: str = _DEFAULT_MODEL,
) -> list[TestQuestion]:
    """
    Generate multiple-choice test questions from retrieved materials.

    Args:
        subject   : Subject name.
        topic     : Topic name.
        materials : RAG chunks or plain strings.
        count     : Number of questions (1–20).
        model     : Ollama model name.

    Returns:
        List of TestQuestion dataclass instances.

    Raises:
        OllamaUnavailableError / OllamaModelError on Ollama issues.
        ContentGenerationError if JSON cannot be parsed.
    """
    count = max(1, min(count, 20))

    if not materials:
        raise ContentGenerationError("No materials provided for test generation.")

    context = _build_context(materials)
    prompt  = _TEST_PROMPT.format(
        subject=subject,
        topic=topic,
        count=count,
        context=context,
    )

    logger.info(
        "Generating {} test questions: subject='{}' topic='{}' model='{}'",
        count, subject, topic, model,
    )

    raw = await _ollama_generate(
        prompt,
        model=model,
        temperature=0.4,
        max_tokens=count * 300,
    )

    return _parse_test_json(raw, subject, topic)


def _parse_test_json(raw: str, subject: str, topic: str) -> list[TestQuestion]:
    """
    Robustly extract and validate a JSON array of questions from LLM output.
    Applies several fallback strategies before raising ContentGenerationError.
    """
    # Strategy 1: direct parse
    try:
        data = json.loads(raw)
        return _validate_questions(data)
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: extract first JSON array with regex
    match = _JSON_ARRAY_RE.search(raw)
    if match:
        try:
            data = json.loads(match.group())
            return _validate_questions(data)
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 3: strip markdown code fences and retry
    cleaned = re.sub(r"```(?:json)?", "", raw).strip()
    try:
        data = json.loads(cleaned)
        return _validate_questions(data)
    except (json.JSONDecodeError, ValueError):
        pass

    logger.error(
        "Failed to parse test JSON for '{}' / '{}'. Raw output:\n{}",
        subject, topic, raw[:500],
    )
    raise ContentGenerationError(
        f"Could not parse test questions from LLM output. "
        f"Try running the model again or increase context quality.\n"
        f"Raw (first 300 chars): {raw[:300]}"
    )


def _validate_questions(data: Any) -> list[TestQuestion]:
    """Validate structure of parsed JSON and return TestQuestion instances."""
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of questions.")

    questions: list[TestQuestion] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i} is not a dict.")

        question = str(item.get("question", "")).strip()
        options  = item.get("options", [])
        correct  = str(item.get("correct_answer", "")).strip().upper()
        explanation = str(item.get("explanation", "")).strip()

        if not question:
            raise ValueError(f"Item {i} missing 'question'.")
        if len(options) != 4:
            raise ValueError(f"Item {i} must have exactly 4 options, got {len(options)}.")
        if correct not in ("A", "B", "C", "D"):
            raise ValueError(f"Item {i} 'correct_answer' must be A/B/C/D, got {correct!r}.")

        questions.append(
            TestQuestion(
                question=question,
                options=[str(o) for o in options],
                correct_answer=correct,
                explanation=explanation,
            )
        )

    if not questions:
        raise ValueError("No valid questions found in response.")

    return questions


# ─── Convenience: sync-friendly dict serialisers ─────────────────────────────

def test_question_to_dict(q: TestQuestion) -> dict:
    return {
        "question":       q.question,
        "options":        q.options,
        "correct_answer": q.correct_answer,
        "explanation":    q.explanation,
    }


# ─── Exceptions ───────────────────────────────────────────────────────────────

class OllamaUnavailableError(Exception):
    """Raised when the Ollama server cannot be reached."""


class OllamaModelError(Exception):
    """Raised when the requested model is not pulled in Ollama."""


class ContentGenerationError(Exception):
    """Raised when content could not be generated or parsed."""
