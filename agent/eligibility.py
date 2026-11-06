"""Delivery-fee eligibility from the policy rules, kept apart from the reply.

The two rules are the late-delivery bullets in the company policy:

- Next Day and Same Day: the delivery fee is refundable when the parcel arrives
  after the expected calendar date.
- Standard: the delivery fee is refundable only when the working-day count is
  greater than 2.

The item value is never part of this decision. This module does not write the
sentence the customer sees.
"""

from __future__ import annotations

import re

LATE_HEADING = "Late deliveries and refunds"
LOSS_HEADING = "Lost or damaged parcels"

_REFUND_QUESTION = re.compile(r"\b(refunds?|money back|fee back|reimburse)\b", re.IGNORECASE)
_LOSS_QUESTION = re.compile(r"\b(lost|damaged|damage|compensation)\b", re.IGNORECASE)

_GRANT = re.compile(
    r"\b(eligible for (?:a |the )?refund|delivery fee is refundable|"
    r"fee is refundable|refund the delivery fee)\b",
    re.IGNORECASE,
)
_DENY = re.compile(
    r"\b(not eligible|isn't eligible|is not eligible|not refundable|"
    r"no refund|refund is not|is not available|not available)\b",
    re.IGNORECASE,
)


def fee_refundable_for_service(service: str, lateness: dict) -> bool | None:
    """Apply the policy rule for this service. None if the parcel is not delivered."""
    if not lateness.get("ok"):
        return None
    if lateness.get("reason") == "not_yet_delivered":
        return None
    name = service.casefold().strip()
    if name == "standard":
        return bool(lateness["standard_delivery_fee_refundable"])
    if name in {"next day", "same day"}:
        return bool(lateness["express_delivery_fee_refundable"])
    return None


def required_policy_heading(question: str) -> str | None:
    """Which policy section a refund or loss question has to be explained from."""
    if _LOSS_QUESTION.search(question):
        return LOSS_HEADING
    if _REFUND_QUESTION.search(question):
        return LATE_HEADING
    return None


def policy_query_for(heading: str) -> str:
    if heading == LATE_HEADING:
        return "late delivery refund delivery fee standard next day same day working days claims"
    if heading == LOSS_HEADING:
        return "lost damaged parcel compensation photos report 28 days 7 days"
    raise ValueError(f"no policy query for {heading}")


def claims_delivery_fee_refund(answer: str) -> bool | None:
    """True if the reply grants a delivery-fee refund, False if it refuses, else None.

    A sentence that says "not eligible" is a refusal even if it also contains
    the words "eligible for a refund".
    """
    grants = False
    denies = False
    for sentence in re.split(r"\n+|(?<=[.!?])\s+", answer or ""):
        if not sentence.strip():
            continue
        if _DENY.search(sentence):
            denies = True
        elif _GRANT.search(sentence):
            grants = True
    if grants and not denies:
        return True
    if denies and not grants:
        return False
    return None


def contradicts_decision(answer: str, decisions: list[dict]) -> dict | None:
    """Return the single order decision the reply disagrees with, or None.

    More than one order is not guessed. A reply that never states eligibility
    is not treated as a contradiction.
    """
    usable = [item for item in decisions if "delivery_fee_refundable" in item]
    if len(usable) != 1:
        return None
    stated = claims_delivery_fee_refund(answer)
    if stated is None:
        return None
    if stated != bool(usable[0]["delivery_fee_refundable"]):
        return usable[0]
    return None


def factual_eligibility_reply(decision: dict) -> str:
    """Last resort when a rewrite still contradicts the record. Not a model sentence."""
    flag = "refundable" if decision["delivery_fee_refundable"] else "not refundable"
    days = decision.get("working_days_after_expected")
    order_id = decision.get("order_id", "this order")
    return (
        f"The delivery record for {order_id} counts {days} working days after the expected date. "
        f"On that record the delivery fee is {flag}. I can't issue a refund from this chat. "
        "Claims go to parcelpigeon.example/claims."
    )
