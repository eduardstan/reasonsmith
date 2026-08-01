"""Command-line interface for reasonsmith v0.2.

What this module is for:
  Provides the CLI entry point (`reasonsmith`, also runnable as `python -m reasonsmith.cli`) to run
  conformance checks on SUT decision logs against formal regulation packs (e.g. `ecoa`,
  `eu_ai_act`, `gdpr`, `table7`), and to validate a requirement pack.

  Usage:
      reasonsmith check --system <decisions.jsonl> --pack <pack_name>
          [--system-name <name>] [--system-scope <class>] [--capabilities <file>] [--json]
      reasonsmith validate-pack <pack_name_or_file> [...]

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
  - `--capabilities <file>` is the only way a CLI run says the system itself claims the signal
    names: without it the adapter derives capabilities from the trace and the report says so,
    and with it — even an empty or comment-only file, which declares nothing — the report says
    the capabilities were declared by the system's maintainers. The two are distinct claims and
    neither may read as the other.
    Why this matters: trace-derived capability names come from one sample log, while a declared
    set is an authoritative system claim, and a finding must say which one it rests on.
  - `validate-pack` prints what the pack contains and exits 0, or exits 1 naming the file and
    the requirement at fault for a pack the loader refuses. It reuses the pack loader exactly,
    so the packs a `check` run can load are exactly the packs `validate-pack` accepts.
    Why this matters: the front door must not have a second, looser idea of a valid pack that
    a stranger could validate a pack with and then fail to check against.

"""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

from reasonsmith.adapters.jsonl import JSONLAdapter
from reasonsmith.report import check_conformance
from reasonsmith.spec import REGULATORY_CLASSES, Pack, list_packs, load_pack
from reasonsmith.verdict import Verdict


def read_capability_declaration(path: str | Path) -> set[str]:
    """Read a capability declaration file into a set of declared signal names.

    Format: one signal name per line. Blank lines and lines whose first non-blank character is
    `#` are ignored, and nothing else is — a line carrying a comma (several names written on
    one line) or whitespace (a phrase, or two names a space silently merged) is refused, naming
    the file and the line, rather than split or guessed at. An empty file, or one of only blank
    and comment lines, declares nothing: that is a distinct claim from having no declaration
    file at all, and it stays distinct through `capability_basis` (see JSONLAdapter).
    """
    file_path = Path(path)
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"Cannot read capability declaration file: {exc}") from exc

    names: set[str] = set()
    for line_num, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "," in line:
            raise ValueError(
                f"Capability declaration {file_path} line {line_num}: expected one signal name "
                f"per line, got {line!r} (the line carries a comma)"
            )
        if any(ch.isspace() for ch in line):
            raise ValueError(
                f"Capability declaration {file_path} line {line_num}: expected a single signal "
                f"name, got {line!r} (whitespace inside the line)"
            )
        names.add(line)
    return names


def format_pack(pack: Pack) -> str:
    """Render a validated pack as the one-line-per-fact summary `validate-pack` prints."""
    lines = [
        f"pack: {pack.id}",
        f"title: {pack.title}",
        f"description: {pack.description}",
    ]
    for key, value in pack.source_metadata.items():
        lines.append(f"source.{key}: {value}")
    lines.append(f"requirements: {len(pack.requirements)}")
    for req in pack.requirements:
        lines.append(
            f"  {req.id} | {req.source_document} {req.article_clause} | {req.formalism} "
            f"| binding: {str(req.binding).lower()} | scope: {req.scope or 'unset'}"
        )
    return "\n".join(lines)


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
            "  1  usage or input error (unknown pack, unreadable system log, unreadable or\n"
            "     malformed capability declaration, or a --system-scope that is not a known\n"
            "     regulatory class).\n"
            "exit codes for validate-pack:\n"
            "  0  every pack loaded and printed.\n"
            "  1  a pack the loader refuses, naming the file and the requirement at fault."
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
        "--capabilities",
        default=None,
        help=(
            "Path to a capability declaration file naming the signals the system can emit, "
            "one per line (`#` starts a comment). With it, the report says the capabilities "
            "were declared by the system's maintainers; without it, capabilities are derived "
            "from the decision log and the report says so"
        ),
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

    validate_parser = subparsers.add_parser(
        "validate-pack",
        help="Validate a requirement pack and print what it contains",
    )
    validate_parser.add_argument(
        "pack",
        nargs="+",
        help=f"Pack name or TOML file path. Built-in packs: {', '.join(list_packs())}",
    )

    parsed = parser.parse_args(args)

    if parsed.command == "validate-pack":
        for name in parsed.pack:
            try:
                pack = load_pack(name)
            except Exception as exc:
                print(f"Error validating pack {name!r}: {exc}", file=sys.stderr)
                return 1
            print(format_pack(pack))
        return 0

    if parsed.command == "check":
        try:
            pack = load_pack(parsed.pack)
        except Exception as exc:
            print(f"Error loading pack {parsed.pack!r}: {exc}", file=sys.stderr)
            return 1

        declared_capabilities = None
        if parsed.capabilities is not None:
            try:
                declared_capabilities = read_capability_declaration(parsed.capabilities)
            except ValueError as exc:
                print(
                    f"Error loading capability declaration {parsed.capabilities!r}: {exc}",
                    file=sys.stderr,
                )
                return 1

        try:
            sut = JSONLAdapter(
                parsed.system, declared_capabilities=declared_capabilities
            )
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
            if args is not None or __name__ == "__main__":
                command = ["python", "-m", "reasonsmith.cli", *cmd_args]
            else:
                command = [sys.argv[0], *cmd_args]
            cmd_str = shlex.join(command)
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
