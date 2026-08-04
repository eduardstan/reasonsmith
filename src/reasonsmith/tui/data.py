"""Report loading and presentation-safe rows for the TUI."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Any

from reasonsmith.adapters.jsonl import JSONLAdapter
from reasonsmith.cli import load_system_module
from reasonsmith.render import AUDIENCES
from reasonsmith.report import ConformanceReport, check_conformance
from reasonsmith.spec import DECISION_DOMAINS, REGULATORY_CLASSES, load_pack


@dataclass(frozen=True)
class TuiOptions:
    """Inputs retained so the user can re-run the same audit from the TUI."""

    pack: str
    system: str | None
    system_module: str | None
    system_name: str
    system_scope: str | None
    system_domains: tuple[str, ...]
    audience: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reasonsmith tui",
        description="Explore one reasonsmith conformance report interactively.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--system", "-s", help="Path to a JSONL decision log")
    source.add_argument(
        "--system-module",
        metavar="MODULE:ATTRIBUTE",
        help="Import a SystemUnderTest or zero-argument factory",
    )
    parser.add_argument("--pack", "-p", required=True, help="Pack name or TOML path")
    parser.add_argument("--system-name", default="SUT")
    parser.add_argument("--system-scope", "--scope", choices=REGULATORY_CLASSES)
    parser.add_argument(
        "--system-domain", action="append", dest="system_domains", choices=DECISION_DOMAINS
    )
    parser.add_argument("--audience", choices=sorted(AUDIENCES), default="auditor")
    return parser


def load_report(args: list[str] | None = None) -> tuple[ConformanceReport, TuiOptions]:
    parsed = build_parser().parse_args(args)
    pack = load_pack(parsed.pack)
    if parsed.system_module:
        cwd = os.getcwd()
        if cwd not in sys.path:
            sys.path.insert(0, cwd)
        sut = load_system_module(parsed.system_module)
    else:
        sut = JSONLAdapter(parsed.system)
    report = check_conformance(
        sut,
        pack,
        system_name=parsed.system_name,
        system_scope=parsed.system_scope,
        system_domains=parsed.system_domains,
    )
    options = TuiOptions(
        pack=parsed.pack,
        system=parsed.system,
        system_module=parsed.system_module,
        system_name=parsed.system_name,
        system_scope=parsed.system_scope,
        system_domains=tuple(parsed.system_domains or ()),
        audience=parsed.audience,
    )
    return report, options


def result_rows(report: ConformanceReport) -> tuple[dict[str, Any], ...]:
    """Expose report findings without inventing values or changing their categories."""
    return tuple(
        {
            "id": result.requirement_id,
            "source": result.source_clause,
            "verdict": result.verdict.value,
            "strength": result.strength.value if result.strength is not None else "not evaluated",
            "evidence": result.evidence_summary,
            "missing": result.signals_missing,
            "required": result.signals_required,
            "details": result.details,
            "binding": result.binding,
            "domains": result.domains,
        }
        for result in report.results
    )
