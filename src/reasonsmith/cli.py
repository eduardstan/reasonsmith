"""Command-line interface for reasonsmith v0.2.

What this module is for:
  Provides the CLI entry point (`reasonsmith.cli`) to run conformance checks on SUT decision
  logs against formal regulation packs (e.g. `ecoa`, `eu_ai_act`, `gdpr`, `table7`).

  Usage:
      python -m reasonsmith.cli check --system <decisions.jsonl> --pack <pack_name>
          [--system-name <name>] [--system-scope <class>] [--json]

What a reader must not break:
  - Exit code contract for `check`: 2 when at least one requirement is VIOLATED, 0 otherwise,
    and 1 on a usage or input error.
    Why this matters: Automation pipelines rely on exit code 2 to distinguish a breach from a
    clean run (0) or a CLI syntax/file error (1).
  - Only a violation is a breach, so only a violation is non-zero. Unattainable, not applicable
    and not evaluated are findings to read in the report, not verdicts against the system: an
    unattainable requirement says the system as built cannot discharge the duty on the evidence
    supplied, a not-applicable one says the duty is limited to a regulatory class this system was
    not declared to be in, and a not-evaluated one says no engine here checked it.
    Why this matters: none of the three is evidence the system failed a duty, so none of them
    fails the caller's build.

"""

from __future__ import annotations

import argparse
import shlex
import sys

from reasonsmith.adapters.jsonl import JSONLAdapter
from reasonsmith.report import check_conformance
from reasonsmith.spec import REGULATORY_CLASSES, list_packs, load_pack
from reasonsmith.verdict import Verdict


def main(args: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reasonsmith",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Audit-grade compliance checking against formal regulation packs.",
        epilog=(
            "exit codes for check:\n"
            "  0  no requirement is violated. Unattainable, not applicable and not evaluated\n"
            "     requirements are reported but are not breaches, so they exit 0 too — read\n"
            "     the report for them.\n"
            "  2  at least one requirement is violated.\n"
            "  1  usage or input error (unknown pack, unreadable system log, or a\n"
            "     --system-scope that is not a known regulatory class)."
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
        "--system-scope",
        "--scope",
        default=None,
        help=(
            "Declared regulatory classification of the system, one of: "
            f"{', '.join(REGULATORY_CLASSES)}. Requirements limited to another class, or to "
            "any class when this is left undeclared, are reported not applicable rather than "
            "assumed to apply. Compared after trimming whitespace and lowercasing; a value "
            "outside that list is a usage error rather than a clean run"
        ),
    )
    check_parser.add_argument(
        "--json",
        action="store_true",
        help="Output report in JSON format",
    )
    check_parser.add_argument(
        "--html",
        nargs="?",
        const="-",
        default=None,
        help="Output report in HTML format to FILE or stdout if omitted / '-'",
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

        try:
            report = check_conformance(
                sut, pack, system_name=parsed.system_name, system_scope=parsed.system_scope
            )
        except (TypeError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        if parsed.html:
            cmd_args = args if args is not None else sys.argv[1:]
            cmd_str = f"python -m reasonsmith.cli {shlex.join(cmd_args)}"
            html_content = report.render_html(command=cmd_str)
            if parsed.html == "-":
                if parsed.json:
                    print(
                        "Error: --json and --html - both write the whole report to stdout, "
                        "so one would be lost. Give --html a FILE.",
                        file=sys.stderr,
                    )
                    return 1
                print(html_content)
            else:
                try:
                    with open(parsed.html, "w", encoding="utf-8") as f:
                        f.write(html_content)
                except OSError as exc:
                    print(f"Error writing HTML report to {parsed.html!r}: {exc}", file=sys.stderr)
                    return 1
                print(report.to_json(indent=2) if parsed.json else report.render_text())
        elif parsed.json:
            print(report.to_json(indent=2))
        else:
            print(report.render_text())

        violations = [r for r in report.results if r.verdict == Verdict.VIOLATED]
        return 2 if violations else 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
