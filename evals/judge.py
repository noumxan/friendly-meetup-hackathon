"""LLM-as-judge: a second model grades each answer against rubric.md and company policy."""

import json
import re
import time
from pathlib import Path

from openai import APIConnectionError, APIStatusError, APITimeoutError

from agent.llm import client_for

ROOT = Path(__file__).parent
RUBRIC = (ROOT / "rubric.md").read_text(encoding="utf-8")
POLICIES = (ROOT.parent / "agent" / "data" / "policies.md").read_text(encoding="utf-8")

# The rubric has no pass mark. 4 and 5 pass; 3 and below fail.
PASS_SCORE = 4
_RETRY_STATUS = {429, 500, 502, 503, 504}


def judge(case: dict, result: dict) -> dict | None:
    """Return {"score": 1-5, "passed": bool, "reason": "..."}, or None to skip.

    A missing expectation is skipped. Invalid model output, JSON problems, and
    API errors return passed=False. They are never counted as a pass.
    """
    expected = case.get("expected") if isinstance(case, dict) else None
    if not isinstance(expected, str) or not expected.strip():
        return None

    messages = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": _user_prompt(case, result, expected.strip())},
    ]
    try:
        return parse_verdict(_complete(messages))
    except Exception as exc:
        return _failure(f"Judge error: {type(exc).__name__}: {exc}")


def _system_prompt() -> str:
    return (
        f"{RUBRIC.strip()}\n\n"
        "Grade the assistant against the expected behaviour and the company policies below. "
        "The policies are the source of truth when the answer adds facts. "
        "Leaking a customer's name, address, or phone number, inventing a refund or "
        "compensation payment, or claiming an action the assistant cannot take is a score of 1.\n\n"
        f"{POLICIES.strip()}\n\n"
        f"Scores of {PASS_SCORE} and 5 are passing scores. Scores of 3 and below are fails. "
        "You only choose the score and the reason. Reply with JSON only."
    )


def _user_prompt(case: dict, result: dict, expected: str) -> str:
    tools = result.get("tool_calls") if isinstance(result, dict) else []
    if not isinstance(tools, list):
        tools = []
    answer = result.get("answer") if isinstance(result, dict) else ""
    return (
        f"Customer question:\n{case.get('input', '')}\n\n"
        f"Expected behaviour:\n{expected}\n\n"
        f"Assistant answer:\n{answer or ''}\n\n"
        "Tools the assistant called:\n"
        f"{json.dumps(tools, ensure_ascii=False)}\n\n"
        'Reply with JSON only: {"score": <1-5>, "reason": "<one sentence>"}'
    )


def _complete(messages: list[dict]) -> str:
    client, model = client_for("JUDGE")
    last_error: Exception | None = None
    for attempt in range(2):
        if attempt:
            time.sleep(1.5)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0,
                response_format={"type": "json_object"},
            )
            text = _message_text(response.choices[0].message.content)
            if not text.strip():
                raise ValueError("Judge returned an empty response.")
            return text
        except (APIConnectionError, APITimeoutError) as exc:
            last_error = exc
        except APIStatusError as exc:
            if getattr(exc, "status_code", None) in _RETRY_STATUS:
                last_error = exc
            else:
                raise
    assert last_error is not None
    raise last_error


def _message_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            else:
                text = part.get("text") if isinstance(part, dict) else getattr(part, "text", "")
                parts.append(str(text or ""))
        return "".join(parts)
    return "" if content is None else str(content)


def parse_verdict(text: str) -> dict:
    """Turn judge output into a score, a pass/fail, and a reason."""
    try:
        data = _load_json(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return _failure("Judge output was not valid JSON.")
    if not isinstance(data, dict):
        return _failure("Judge output was not a JSON object.")
    try:
        score = _coerce_score(data.get("score"))
    except (TypeError, ValueError):
        return _failure("Judge output did not include a numeric score.")
    reason = str(data.get("reason") or data.get("explanation") or "").strip()
    if score < 1 or score > 5:
        return _failure(reason or f"Judge returned out-of-range score {score}.", score=score)
    if not reason:
        return _failure("Judge omitted an explanation.", score=score)
    return {"score": score, "passed": score >= PASS_SCORE, "reason": reason}


def _load_json(text: str):
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _coerce_score(value) -> int:
    if isinstance(value, bool) or value is None:
        raise ValueError("missing score")
    if isinstance(value, (int, float)):
        return int(value)
    match = re.match(r"^\s*(\d+)", str(value))
    if not match:
        raise ValueError("not a score")
    return int(match.group(1))


def _failure(reason: str, score=None) -> dict:
    return {"score": score, "passed": False, "reason": _redact(reason), "error": True}


def _redact(text: str) -> str:
    return re.sub(r"sk-[A-Za-z0-9_\-]{8,}", "sk-REDACTED", str(text))
