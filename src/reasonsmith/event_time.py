"""Pure-Python event-time parsing and bounded-response measurement.

This module is deliberately smaller than a metric-temporal-logic engine.  It accepts only
explicit-offset ISO-8601 timestamps and fixed durations (hours, days, or calendar months),
normalises instants to UTC, and supplies the arithmetic used by the one ``within_after``
property-language construct.  It does not infer event identity or legal applicability; the
observed engine supplies those from the trace and reports uncertainty as not evaluated.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Final


class EventTimeError(ValueError):
    """A timestamp or bounded-response duration is outside the documented contract."""


# RFC-3339-like subset: seconds are required, fractional seconds are optional, and an explicit
# offset is mandatory.  A numeric offset makes a local wall-clock value unambiguous; UTC ``Z`` is
# the preferred spelling.  We intentionally do not accept a date-only or naive timestamp.
_TIMESTAMP_RE: Final = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})T(?P<time>\d{2}:\d{2}:\d{2})"
    r"(?P<fraction>\.\d{1,6})?(?P<offset>Z|[+-]\d{2}:\d{2})$"
)
_DURATION_RE: Final = re.compile(
    r"^(?P<amount>\d+)(?P<unit>h|hour|hours|d|day|days|mo|month|months)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Duration:
    """A finite deadline window, measured as elapsed time or calendar months."""

    amount: int
    unit: str

    @property
    def is_calendar(self) -> bool:
        return self.unit == "months"

    @property
    def text(self) -> str:
        suffix = {"hours": "h", "days": "d", "months": "mo"}[self.unit]
        return f"{self.amount}{suffix}"

    @property
    def elapsed(self) -> timedelta | None:
        if self.unit == "hours":
            return timedelta(hours=self.amount)
        if self.unit == "days":
            return timedelta(days=self.amount)
        return None


@dataclass(frozen=True)
class EventPair:
    """One correlated anchor/end pair and the arithmetic a reader can re-check."""

    case_id: str
    anchor_timestamp: datetime
    end_timestamp: datetime
    delta_seconds: float
    deadline_timestamp: datetime
    within_bound: bool
    anchor_record_index: int
    end_record_index: int

    def payload(self, bound: Duration) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "anchor_timestamp": format_timestamp(self.anchor_timestamp),
            "end_timestamp": format_timestamp(self.end_timestamp),
            "delta_seconds": self.delta_seconds,
            "bound": bound.text,
            "deadline_timestamp": format_timestamp(self.deadline_timestamp),
            "within_bound": self.within_bound,
            "anchor_record_index": self.anchor_record_index,
            "end_record_index": self.end_record_index,
        }


def parse_timestamp(value: str) -> datetime:
    """Parse one explicit-offset timestamp and return its UTC instant.

    Accepted values are ``YYYY-MM-DDTHH:MM:SS[.ffffff]Z`` or the same form with a
    ``+HH:MM``/``-HH:MM`` offset.  A naive value, malformed value, ``-00:00`` (unknown
    offset), or a value outside :class:`datetime`'s range is refused.  Because the offset is
    explicit, a daylight-saving fold cannot be silently selected.
    """

    if not isinstance(value, str):
        raise EventTimeError(f"timestamp must be a string, got {type(value).__name__}")
    match = _TIMESTAMP_RE.fullmatch(value)
    if match is None:
        raise EventTimeError(
            f"invalid timestamp {value!r}; expected YYYY-MM-DDTHH:MM:SS[.ffffff]Z or an explicit "
            "±HH:MM offset"
        )
    if match.group("offset") == "-00:00":
        raise EventTimeError("timestamp offset -00:00 is unknown and cannot identify an instant")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EventTimeError(f"invalid timestamp {value!r}: {exc}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EventTimeError(f"timestamp {value!r} is naive; an explicit offset is required")
    try:
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise EventTimeError(f"timestamp {value!r} cannot be normalised to UTC: {exc}") from exc


def _utc_instant(value: datetime) -> datetime:
    """Return an aware UTC instant, refusing the host machine's local timezone fallback."""
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise EventTimeError("event arithmetic requires an aware timestamp with an explicit offset")
    return value.astimezone(timezone.utc)


def format_timestamp(value: datetime) -> str:
    """Format a UTC instant in the canonical wire spelling used in result details."""

    utc = _utc_instant(value)
    return utc.isoformat(timespec="auto").replace("+00:00", "Z")


def parse_duration(value: str) -> Duration:
    """Parse the deliberately small duration vocabulary used by ``within_after``.

    ``h`` and ``d`` are elapsed hours/days.  ``mo``/``month``/``months`` are calendar months:
    adding one month to 31 January clamps to the last day of February.  No 30/180-day conversion
    is ever made.
    """

    if not isinstance(value, str):
        raise EventTimeError(f"duration must be a string such as '24h' or '1mo', got {value!r}")
    match = _DURATION_RE.fullmatch(value.strip())
    if match is None:
        raise EventTimeError(
            f"invalid duration {value!r}; use a non-negative integer followed by h, d, or mo"
        )
    amount = int(match.group("amount"))
    unit = match.group("unit").lower()
    canonical = "hours" if unit in {"h", "hour", "hours"} else (
        "days" if unit in {"d", "day", "days"} else "months"
    )
    return Duration(amount, canonical)


def add_calendar_months(start: datetime, months: int) -> datetime:
    """Add calendar months in UTC, clamping an end-of-month day when needed."""

    if months < 0:
        raise EventTimeError("calendar duration must not be negative")
    utc = _utc_instant(start)
    month_index = utc.year * 12 + (utc.month - 1) + months
    year, month_index = divmod(month_index, 12)
    month = month_index + 1
    try:
        day = min(utc.day, calendar.monthrange(year, month)[1])
        return utc.replace(year=year, month=month, day=day)
    except (OverflowError, ValueError) as exc:
        raise EventTimeError(
            f"a deadline {months} calendar month(s) after {utc.isoformat()} is outside the "
            f"representable range of an instant: {exc}"
        ) from exc


def deadline_for(start: datetime, duration: Duration) -> datetime:
    """Return the inclusive end instant for a duration from ``start``.

    A bound the duration grammar accepts can still name an instant no :class:`datetime` can hold.
    That is an evidence refusal about this pair, reported as an :class:`EventTimeError` like every
    other one, rather than an arithmetic exception escaping the engine that called it.
    """

    if duration.is_calendar:
        return add_calendar_months(start, duration.amount)
    anchor = _utc_instant(start)
    try:
        elapsed = duration.elapsed
        assert elapsed is not None
        return anchor + elapsed
    except OverflowError as exc:
        raise EventTimeError(
            f"a deadline {duration.text} after {anchor.isoformat()} is outside the representable "
            f"range of an instant: {exc}"
        ) from exc


def measure_pair(
    case_id: str,
    anchor_timestamp: datetime,
    end_timestamp: datetime,
    bound: Duration,
    *,
    anchor_record_index: int,
    end_record_index: int,
) -> EventPair:
    """Measure a pair under closed, forward deadline semantics.

    The caller decides whether the event records are correlated and unique.  This function refuses
    an end before the anchor (including an out-of-order trace position) rather than turning it into
    a negative passing latency.  The bound is inclusive: ``0 <= end - start <= deadline``.
    """

    anchor = _utc_instant(anchor_timestamp)
    end = _utc_instant(end_timestamp)
    if end_record_index < anchor_record_index:
        raise EventTimeError("end event occurs before its anchor in the trace")
    deadline = deadline_for(anchor, bound)
    delta = (end - anchor).total_seconds()
    if delta < 0:
        raise EventTimeError("end timestamp is before its anchor timestamp")
    return EventPair(
        case_id=case_id,
        anchor_timestamp=anchor,
        end_timestamp=end,
        delta_seconds=delta,
        deadline_timestamp=deadline,
        within_bound=end <= deadline,
        anchor_record_index=anchor_record_index,
        end_record_index=end_record_index,
    )


TIMEZONE_POLICY = "timestamps require an explicit ISO-8601 offset and are normalised to UTC"
CALENDAR_POLICY = (
    "h/d are elapsed time; mo/month(s) use calendar arithmetic with end-of-month clamping"
)

__all__ = [
    "CALENDAR_POLICY",
    "Duration",
    "EventPair",
    "EventTimeError",
    "TIMEZONE_POLICY",
    "add_calendar_months",
    "deadline_for",
    "format_timestamp",
    "measure_pair",
    "parse_duration",
    "parse_timestamp",
]
