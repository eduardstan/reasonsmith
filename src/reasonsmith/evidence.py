"""The evidence emitter: Table 7 rows in, minimal evidence records out.

What this module is for:
  Emits minimal evidence records according to Table 7 duties, checking structural completeness
  and explicitly naming missing fields without throwing errors or filling gaps.

  Core governing rule:
    A record missing a required field is reported as INCOMPLETE, and the missing fields are named.
    A partial record presented as complete would launder a compliance gap into a document that
    reads as authoritative, which is worse than emitting nothing.

What a reader must not break:
  - `emit` never raises for a missing field; it marks the record INCOMPLETE and lists what is
    absent.
    Why this matters: Refusing to produce anything would hide the gap just as effectively as
    filling it; emitting the record marked INCOMPLETE exposes what is absent.
  - A key not in the duty's Table 7 row is rejected outright; unlisted fields cannot substitute
    for required ones.
    Why this matters: Accepting unlisted keys would let a field nobody required stand in for one
    somebody did.
  - Non-Table 7 material travels in `attachments` and renders under its own heading.
    Why this matters: Ensures non-Table 7 data can never be read as discharging part of the row.
  - No default, inference, or dummy fallback may ever be substituted for a missing field.
    Why this matters: Substituting defaults would launder missing compliance data into complete
    records.
"""

from __future__ import annotations

import copy
import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

TABLE7_PATH = Path(__file__).with_name("table7.toml")

LIMITS = (
    "This record is not a compliance guarantee and is not legal advice. It reproduces the minimal "
    "evidence fields that one peer-reviewed review (Table 7 of the source named above) associates "
    "with the cited duty. Whether those fields discharge the duty, and whether the values supplied "
    "for them are accurate, are determinations this tool does not make and cannot make."
)


def _load() -> tuple[dict, dict]:
    with TABLE7_PATH.open("rb") as fh:
        raw = tomllib.load(fh)
    return raw["source"], {d["id"]: d for d in raw["duty"]}


SOURCE, DUTIES = _load()


def duty(duty_id: str) -> dict:
    """The Table 7 row with this id, as loaded from table7.toml."""
    try:
        return DUTIES[duty_id]
    except KeyError:
        raise KeyError(
            f"no Table 7 duty {duty_id!r}; the table has six rows: {', '.join(DUTIES)}"
        ) from None


def required_keys(duty_id: str) -> list[str]:
    """The keys of the duty's 'Minimal evidence to retain' column, in table order."""
    return [f["key"] for f in duty(duty_id)["evidence_field"]]


@dataclass(frozen=True)
class Record:
    """A minimal evidence record for one decision under one duty.

    `missing` is the part that matters: the required keys whose values were not supplied. It is
    empty exactly when the record is complete with respect to Table 7.
    """

    duty_id: str
    decision_id: str
    fields: dict
    missing: tuple[str, ...]
    attachments: dict = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return not self.missing

    @property
    def status(self) -> str:
        return "COMPLETE" if self.complete else "INCOMPLETE"

    def missing_report(self) -> list[str]:
        """The missing fields as 'key — verbatim Table 7 text', for a reader without the paper."""
        text = {f["key"]: f["table7_text"] for f in duty(self.duty_id)["evidence_field"]}
        return [f"{k} — {text[k]}" for k in self.missing]

    def render(self) -> str:
        d = duty(self.duty_id)
        out = [
            f"EVIDENCE RECORD [{self.status}]",
            f"decision: {self.decision_id}",
            f"duty: {d['requirement']}",
            f"legal source: {d['legal_source']}",
            f"source of the duty: {SOURCE['table']} (row {d['table7_row']}, p. {SOURCE['page']}), "
            f"{SOURCE['paper']}, {SOURCE['authors']}, {SOURCE['venue']}, "
            f"{SOURCE['publication_date']}",
            f"symbolic artifact(s) Table 7 asks for: {'; '.join(d['symbolic_artifacts'])}",
            f"where it fits: {'; '.join(d['lifecycle_placement'])}",
            "",
            "minimal evidence retained:",
        ]
        text = {f["key"]: f["table7_text"] for f in d["evidence_field"]}
        for key in required_keys(self.duty_id):
            if key in self.fields:
                out.append(f"  [x] {key} ({text[key]}):")
                for line in str(self.fields[key]).splitlines() or [""]:
                    out.append(f"        {line}")
            else:
                out.append(f"  [ ] {key} ({text[key]}): NOT PRODUCED")
        if self.missing:
            out += [
                "",
                f"INCOMPLETE: {len(self.missing)} of {len(required_keys(self.duty_id))} required "
                f"fields could not be produced. This record does not carry the minimal evidence "
                f"Table 7 specifies for this duty. Missing:",
            ]
            out += [f"  - {line}" for line in self.missing_report()]
        if self.attachments:
            out += ["", "supporting material (NOT Table 7 evidence, and fills no gap above):"]
            for k, v in self.attachments.items():
                out.append(f"  {k}:")
                for line in str(v).splitlines():
                    out.append(f"    {line}")
        out += ["", "LIMITS OF THIS RECORD", f"  {LIMITS}"]
        return "\n".join(out)

    def to_dict(self) -> dict:
        d = duty(self.duty_id)
        return {
            "status": self.status,
            "complete": self.complete,
            "duty_id": self.duty_id,
            "table7_row": d["table7_row"],
            "decision_id": self.decision_id,
            "duty": d["requirement"],
            "legal_source": d["legal_source"],
            "table7_source": copy.deepcopy(SOURCE),
            "symbolic_artifacts": list(d["symbolic_artifacts"]),
            "lifecycle_placement": list(d["lifecycle_placement"]),
            "fields": dict(self.fields),
            "missing": list(self.missing),
            "missing_report": self.missing_report(),
            "attachments": dict(self.attachments),
            "limits": LIMITS,
        }

    def to_json(self, indent: int | None = None) -> str:
        """JSON for `to_dict`. Values outside JSON's own types are stringified exactly as
        `render` prints them, so a field carrying an arbitrary object serialises rather than
        raising."""
        return json.dumps(self.to_dict(), indent=indent, default=str, allow_nan=False)


def emit(duty_id: str, decision_id: str, fields: dict, attachments: dict | None = None) -> Record:
    """Build the minimal evidence record for `duty_id`, naming every required field it lacks.

    A field counts as supplied only if its key carries a value that is not None and not blank; an
    empty string is an absent field wearing a present field's clothes, so it is reported missing.
    Keys outside the duty's Table 7 row are rejected rather than stored.
    """
    required = required_keys(duty_id)
    unknown = sorted(set(fields) - set(required))
    if unknown:
        raise ValueError(
            f"{unknown} are not evidence fields of Table 7 row {duty(duty_id)['table7_row']} "
            f"({duty_id}); its fields are {required}. Material that is not Table 7 evidence "
            f"belongs in `attachments`, where it cannot be read as discharging the duty."
        )
    supplied = {k: v for k, v in fields.items() if v is not None and str(v).strip() != ""}
    missing = tuple(k for k in required if k not in supplied)
    return Record(duty_id, decision_id, supplied, missing, dict(attachments or {}))


def traceability_report() -> str:
    """Every schema entry beside the Table 7 text it was transcribed from, so a reader can check
    this package against the printed table without owning the PDF."""
    out = [
        f"{SOURCE['table']}. {SOURCE['caption']}",
        f"{SOURCE['paper']} — {SOURCE['authors']}, {SOURCE['venue']}, {SOURCE['publication_date']}",
        f"Section {SOURCE['section']}, p. {SOURCE['page']}. "
        f"Columns: {', '.join(SOURCE['columns'])}.",
    ]
    for d in DUTIES.values():
        out += [
            "",
            f"row {d['table7_row']}: {d['id']}",
            f"  Requirement                     : {d['requirement']}",
            f"  Legal source                    : {d['legal_source']}",
            f"  Symbolic artifact(s) to provide : {'; '.join(d['symbolic_artifacts'])}",
            "  Minimal evidence to retain      :",
        ]
        out += [f"      {f['key']:<38} <- {f['table7_text']}" for f in d["evidence_field"]]
        out.append(f"  Where it fits                   : {'; '.join(d['lifecycle_placement'])}")
    return "\n".join(out)
