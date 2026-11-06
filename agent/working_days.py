"""Working-day arithmetic for Parcel Pigeon.

A delivery is N working days late when there are N working days strictly after
the expected date, up to and including the actual delivery date. The expected
date itself is not counted. Saturday, Sunday, and England-and-Wales bank
holidays are not working days.

The count is deterministic. Callers must not ask a language model to do it.

Bank holidays follow the England and Wales pattern: New Year's Day, Good Friday,
Easter Monday, the first Monday in May, the last Monday in May, the last Monday
in August, Christmas Day, and Boxing Day, with the usual weekend substitute day.
Scotland and Northern Ireland have extra days. The company policy says "UK bank
holidays" and does not say which nation, so this is an explicit limitation.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta


class DateError(ValueError):
    """A date string was missing or not an ISO calendar date."""


def parse_iso_date(value: object) -> date:
    if not isinstance(value, str) or not value.strip():
        raise DateError("missing date")
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise DateError(f"invalid date: {value}") from exc


def easter_sunday(year: int) -> date:
    """Gregorian Easter Sunday, from the Anonymous algorithm."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month = (h + ell - 7 * m + 114) // 31
    day = ((h + ell - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _nth_monday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    offset = (0 - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_monday(year: int, month: int) -> date:
    if month == 12:
        last = date(year, 12, 31)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return last - timedelta(days=last.weekday())


def _weekend_substitute(day: date) -> date:
    if day.weekday() == 5:
        return day + timedelta(days=2)
    if day.weekday() == 6:
        return day + timedelta(days=1)
    return day


def _christmas_and_boxing(year: int) -> set[date]:
    """Christmas Day and Boxing Day, moved off the weekend without a clash."""
    christmas = date(year, 12, 25)
    boxing = date(year, 12, 26)
    if christmas.weekday() == 5:
        return {christmas + timedelta(days=2), christmas + timedelta(days=3)}
    if christmas.weekday() == 6:
        return {boxing, boxing + timedelta(days=1)}
    if boxing.weekday() == 5:
        return {christmas, boxing + timedelta(days=2)}
    return {christmas, boxing}


def bank_holidays(year: int, *, region: str = "england-and-wales") -> set[date]:
    if region != "england-and-wales":
        raise ValueError(f"unsupported bank-holiday region: {region}")
    if year < 1970 or year > 2100:
        raise ValueError(f"year out of supported range: {year}")
    easter = easter_sunday(year)
    days = {
        _weekend_substitute(date(year, 1, 1)),
        easter - timedelta(days=2),
        easter + timedelta(days=1),
        _nth_monday(year, 5, 1),
        _last_monday(year, 5),
        _last_monday(year, 8),
    }
    days.update(_christmas_and_boxing(year))
    return days


def is_working_day(day: date) -> bool:
    return day.weekday() < 5 and day not in bank_holidays(day.year)


def working_days_after(start: date, end: date) -> int:
    """Working days in (start, end]. Negative when end is before start."""
    if end < start:
        return -working_days_after(end, start)
    count = 0
    day = start + timedelta(days=1)
    while day <= end:
        if is_working_day(day):
            count += 1
        day += timedelta(days=1)
    return count


def assess_lateness(expected: object, actual: object) -> dict:
    """Compare an expected delivery date with the date it arrived.

    Returns a JSON-ready dict. Invalid input sets ok=False and does not guess.
    """
    try:
        start = parse_iso_date(expected)
        end = parse_iso_date(actual)
    except DateError as exc:
        return {"ok": False, "error": str(exc)}
    calendar_days = (end - start).days
    working_days = working_days_after(start, end)
    return {
        "ok": True,
        "expected": start.isoformat(),
        "actual": end.isoformat(),
        "calendar_days_after_expected": calendar_days,
        "working_days_after_expected": working_days,
        "early": calendar_days < 0,
        "on_time": calendar_days == 0,
        "late": calendar_days > 0,
        "standard_delivery_fee_refundable": working_days > 2,
        "express_delivery_fee_refundable": calendar_days > 0,
        "bank_holiday_region": "england-and-wales",
        "counting_rule": "working days strictly after the expected date, up to and including the delivery date",
    }
