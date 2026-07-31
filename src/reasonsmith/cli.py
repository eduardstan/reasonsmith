"""Command-line interface for reasonsmith v0.2.

Usage:
    python -m reasonsmith.cli check --system <decisions.jsonl> --pack <pack_name>
        [--system-name <name>]

Exit codes for `check`: 0 when no requirement is violated or unattainable, 2 when at least
one is, 1 on a usage or input error. A requirement that was not evaluated is not a finding
against the system, so it does not change the exit code.
"""

from __future__ import annotations

import argparse
import sys

from reasonsmith.adapters.jsonl import JSONLAdapter
from reasonsmith.report import check_conformance
from reasonsmith.spec import list_packs, load_pack
from reasonsmith.verdict import Strength, Verdict


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reasonsmith",
        description=(
            "Audit-grade compliance checking against formal regulation packs. "
            "check exits 2 when a requirement is violated or unattainable, 0 otherwise."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    check_parser = subparsers.add_parser("check", help="Check SUT conformance against a pack")
    check_parser.add_argument(
        "--system",
        "-s",
        required=True,
        help="Path to JSONL decision log file or system specification",
    )
    check_parser.add_argument(
        "--pack",
        "-p",
        required=True,
        help=f"Pack name or file path. Built-in packs: {', '.join(list_packs())}",
    )
    check_parser.add_argument(
        "--system-name",
        default="SUT",
        help="Name of system under test for the report",
    )
    check_parser.add_argument(
        "--json",
        action="store_true",
        help="Output report in JSON format",
    )

    parsed = parser.parse_args(args)

    if parsed.command == "check":
        try:
            pack = load_pack(parsed.pack)
        except Exception as exc:
            print(f"Error loading pack {parsed.pack!r}: {exc}", file=sys.stderr)
            return 1

        try:
            sut = JSONLAdapter(parsed.system)
        except Exception as exc:
            print(f"Error loading system log {parsed.system!r}: {exc}", file=sys.stderr)
            return 1

        report = check_conformance(sut, pack, system_name=parsed.system_name)

        if parsed.json:
            print(report.to_json(indent=2))
        else:
            print(report.render_text())

        findings = [
            r
            for r in report.results
            if r.verdict == Verdict.VIOLATED or r.strength == Strength.UNATTAINABLE
        ]
        return 2 if findings else 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
