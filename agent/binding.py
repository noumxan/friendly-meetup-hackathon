"""Bind order-related tool calls to the order record the customer named.

A single order ID in the question is authoritative. Dates the model invents
are not used for that order. An order ID the model adds, when the customer
named a different one, is rejected rather than replaced. Several order IDs are
not guessed between.
"""

from __future__ import annotations

import json
import re

_ORDER_ID = re.compile(r"\bPP-\d+\b", re.IGNORECASE)


def mentioned_order_ids(text: str) -> list[str]:
    found: list[str] = []
    for match in _ORDER_ID.findall(text or ""):
        order_id = match.upper()
        if order_id not in found:
            found.append(order_id)
    return found


def prepare_tool_call(question: str, name: str, args: dict) -> tuple[dict, str | None]:
    """Return arguments to run, or an error payload when the call must not run.

    The error is a JSON string. Callers must not substitute a different order.
    """
    if not isinstance(args, dict):
        return {}, json.dumps({"ok": False, "error": "invalid_arguments"})
    user_ids = mentioned_order_ids(question)
    if name == "get_order":
        return _bind_order_id(user_ids, args, "order_id")
    if name == "working_days_between":
        return _bind_lateness(user_ids, args)
    return args, None


def _bind_order_id(user_ids: list[str], args: dict, field: str) -> tuple[dict, str | None]:
    requested = str(args.get(field) or "").strip().upper()
    if user_ids and requested and requested not in user_ids:
        return args, _mismatch(requested, user_ids)
    if requested:
        bound = dict(args)
        bound[field] = requested
        return bound, None
    return args, None


def _bind_lateness(user_ids: list[str], args: dict) -> tuple[dict, str | None]:
    requested = str(args.get("order_id") or "").strip().upper()
    if requested:
        if user_ids and requested not in user_ids:
            return args, _mismatch(requested, user_ids)
        if not user_ids:
            return args, json.dumps(
                {
                    "ok": False,
                    "error": "order_id_not_in_question",
                    "requested_order_id": requested,
                }
            )
        bound = {"order_id": requested}
        if args.get("start_date") or args.get("end_date"):
            bound["start_date"] = args.get("start_date")
            bound["end_date"] = args.get("end_date")
        return bound, None
    if len(user_ids) == 1:
        bound = {"order_id": user_ids[0]}
        if args.get("start_date") or args.get("end_date"):
            bound["start_date"] = args.get("start_date")
            bound["end_date"] = args.get("end_date")
        return bound, None
    if len(user_ids) > 1:
        return args, json.dumps(
            {
                "ok": False,
                "error": "multiple_order_ids",
                "order_ids_in_question": user_ids,
            }
        )
    return args, None


def _mismatch(requested: str, user_ids: list[str]) -> str:
    return json.dumps(
        {
            "ok": False,
            "error": "order_id_mismatch",
            "requested_order_id": requested,
            "order_ids_in_question": user_ids,
        }
    )
