"""Block claims the assistant has no tool to carry out.

This does not edit words inside an otherwise good answer. A violating reply is
rejected as a whole. Negated sentences such as "I cannot issue a refund" are
allowed. Eligibility ("you can claim the delivery fee") is not a promise to pay.
"""

from __future__ import annotations

import re

SAFE_FALLBACK = (
    "I can't take that action from this chat. I can't issue refunds, pay compensation, "
    "submit a claim, change a delivery address, or verify your identity. "
    "For a refund or a compensation claim, use parcelpigeon.example/claims. "
    "You can also email help@parcelpigeon.example."
)

_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "refund_promise",
        re.compile(
            r"\b(i|we)\b(?:\s+\w+){0,5}\s+"
            r"(can|will|could|shall|have|'ll|'ve)\b(?:\s+\w+){0,8}\s+"
        r"(issu\w*|process\w*|pay\w*|complet\w*|arrang\w*|sort\w*)\b(?:\s+\w+){0,6}\s+"
        r"(the |your |a )?refund",
            re.IGNORECASE,
        ),
    ),
    (
        "refund_confirmed",
        re.compile(
            r"\b(?:"
            r"refund has been (?:issued|processed|completed|paid|sent)|"
            r"consider it refunded|"
            r"(?:it is|it's) refunded|"
            r"money is on its way back|"
            r"(?:processed|paid) your refund"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "refund_direct",
        re.compile(
            r"\b(?:(?:can|will|'ll) refund you|refund you directly)\b|"
            r"\b(?:i'll|we'll)\s+(?:just\s+)?(?:sort|send|pay|issue|process)\w*\b(?:\s+\w+){0,4}\s+(?:the |your |a )?refund\b|"
            r"\bsend the £[\d.,]+ back\b",
            re.IGNORECASE,
        ),
    ),
    (
        "identity_workflow",
        re.compile(
            r"\b(verify your identity|identity verification|verification step|"
            r"guide you through verifying|verifying your identity)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "address_changed",
        re.compile(
            r"\b((i|we)('ve| have)? (changed|updated) (the |your )?delivery address|"
            r"address has been (changed|updated))\b",
            re.IGNORECASE,
        ),
    ),
    (
        "claim_submitted",
        re.compile(
            r"\b(i|we)\b(?:\s+\w+){0,4}\s+(can|will|have|'ll|'ve)\b(?:\s+\w+){0,6}\s+"
            r"(file|submit|lodge|send)\b(?:\s+\w+){0,4}\s+(the |your |a )?claim",
            re.IGNORECASE,
        ),
    ),
)

_NEGATION = re.compile(
    r"\b(not|no|never|cannot|can't|won't|unable|don't|do not|without)\b",
    re.IGNORECASE,
)


def find_violations(answer: str) -> list[str]:
    """Return violation names found in a customer-facing reply."""
    if not isinstance(answer, str) or not answer.strip():
        return []
    found: list[str] = []
    for name, pattern in _RULES:
        for match in pattern.finditer(answer):
            if _negated(answer, match.start(), match.end()):
                continue
            if name not in found:
                found.append(name)
    return found


def _negated(text: str, start: int, end: int) -> bool:
    """A claim is negated when its sentence denies it before the claim.

    "I can't issue a refund" is allowed. "I can't see it, but I will issue
    the refund" is not, because "but" starts a new claim.
    """
    sentence_start = 0
    for mark in range(start - 1, -1, -1):
        if text[mark] in ".!?\n":
            sentence_start = mark + 1
            break
    before = text[sentence_start:start]
    matched = text[start:end]
    if _NEGATION.search(matched) and re.search(r"\bbut\b", matched, re.IGNORECASE) is None:
        return True
    negation = _NEGATION.search(before)
    if negation is None:
        return False
    return re.search(r"\bbut\b", before[negation.end() :], re.IGNORECASE) is None
