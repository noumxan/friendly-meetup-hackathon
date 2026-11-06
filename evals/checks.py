"""Deterministic checks: fast, free and repeatable.

Each check gets the agent's `result` and the `value` from the test case, and returns
True for a pass or False for a fail. A bad value or a broken result is a fail,
never a silent skip.

`result` looks like:
  {"answer": "...", "tool_calls": [{"name": "get_order", "args": {"order_id": "PP-1001"}}],
   "latency_s": 3.2, "tokens": 812}
"""

import re


def _answer(result: dict) -> str:
    answer = result.get("answer") if isinstance(result, dict) else ""
    return answer if isinstance(answer, str) else ""


def _calls(result: dict) -> list[dict]:
    if not isinstance(result, dict):
        return []
    calls = result.get("tool_calls")
    if not isinstance(calls, list):
        return []
    return [call for call in calls if isinstance(call, dict)]


def contains(result: dict, value: str) -> bool:
    """Required content, matched case-insensitively."""
    if not isinstance(value, str) or value == "":
        return False
    return value.lower() in _answer(result).lower()


def not_contains(result: dict, value: str) -> bool:
    """Prohibited content. An empty answer still passes, because the phrase is absent."""
    if not isinstance(value, str) or value == "":
        return False
    return value.lower() not in _answer(result).lower()


def tool_called(result: dict, value: str) -> bool:
    """True when the agent called the tool named `value`."""
    if not isinstance(value, str) or not value.strip():
        return False
    name = value.strip()
    return any(call.get("name") == name for call in _calls(result))


def tool_not_called(result: dict, value: str) -> bool:
    """True when the agent did not call the tool named `value`."""
    if not isinstance(value, str) or not value.strip():
        return False
    return not tool_called(result, value)


def _same_arg(actual, expected) -> bool:
    if isinstance(expected, str) or isinstance(actual, str):
        if actual is None:
            return False
        return str(actual).strip().casefold() == str(expected).strip().casefold()
    return actual == expected


def tool_called_with(result: dict, value: dict) -> bool:
    """True when one call used this tool and every expected argument.

    `value` is {"name": "get_order", "args": {"order_id": "PP-1001"}}.
    Extra arguments on the call are allowed. Strings match after stripping
    and ignoring case, so "pp-1001" matches "PP-1001".
    """
    if not isinstance(value, dict) or not isinstance(value.get("name"), str):
        return False
    expected_args = value.get("args") or {}
    if not isinstance(expected_args, dict):
        return False
    for call in _calls(result):
        if call.get("name") != value["name"]:
            continue
        args = call.get("args")
        if not isinstance(args, dict):
            continue
        if all(_same_arg(args.get(key), expected) for key, expected in expected_args.items()):
            return True
    return False


def no_tools(result: dict, value=None) -> bool:
    """True when the agent called no tools. `value` is ignored."""
    return len(_calls(result)) == 0


def no_unexpected_tools(result: dict, value) -> bool:
    """True when every tool call is in the allowed list.

    `value` is a list of tool names, or a single tool name. An empty list
    means any tool call is unexpected.
    """
    if isinstance(value, str):
        allowed = {value}
    elif isinstance(value, list) and all(isinstance(name, str) for name in value):
        allowed = set(value)
    else:
        return False
    return all(call.get("name") in allowed for call in _calls(result))


def max_seconds(result: dict, value) -> bool:
    """True when the answer arrived within `value` seconds."""
    if not isinstance(result, dict) or result.get("error"):
        return False
    try:
        limit = float(value)
        latency = float(result["latency_s"])
    except (TypeError, ValueError, KeyError):
        return False
    return latency <= limit


def max_words(result: dict, value) -> bool:
    """True when the answer has at most `value` words."""
    try:
        limit = int(value)
    except (TypeError, ValueError):
        return False
    if isinstance(value, bool) or limit < 0:
        return False
    return len(_answer(result).split()) <= limit


def no_prohibited_claim(result: dict, value=None) -> bool:
    """True when the answer does not claim an action the assistant cannot take.

    `value` is ignored. Negated refusals such as "I cannot issue a refund" pass.
    """
    from agent.guard import find_violations

    return not find_violations(_answer(result))


def matches_regex(result: dict, value: str) -> bool:
    """True when the answer matches the regular expression in `value`."""
    if not isinstance(value, str) or value == "":
        return False
    try:
        pattern = re.compile(value, re.IGNORECASE)
    except re.error:
        return False
    return pattern.search(_answer(result)) is not None


CHECKS = {
    "contains": contains,
    "not_contains": not_contains,
    "tool_called": tool_called,
    "tool_not_called": tool_not_called,
    "tool_called_with": tool_called_with,
    "no_tools": no_tools,
    "no_unexpected_tools": no_unexpected_tools,
    "max_seconds": max_seconds,
    "max_words": max_words,
    "matches_regex": matches_regex,
    "no_prohibited_claim": no_prohibited_claim,
}
