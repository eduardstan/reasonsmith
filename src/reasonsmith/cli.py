"""Command-line interface for reasonsmith v0.2.

What this module is for:
  Provides the CLI entry point (`reasonsmith`, also runnable as `python -m reasonsmith.cli`) to run
  conformance checks on SUT decision logs against formal regulation packs (e.g. `ecoa`,
  `eu_ai_act`, `gdpr`, `table7`), and to validate a requirement pack.

  Usage:
      reasonsmith check --system <decisions.jsonl> --pack <pack_name>
          [--system-name <name>] [--system-scope <class>] [--system-domain <domain>]...
          [--capabilities <file>] [--audience <reader>] [--json]
      reasonsmith check --system-module <module>:<attribute> --pack <pack_name> [...]
      reasonsmith validate-pack <pack_name_or_file> [...]
      reasonsmith explain <requirement_id> [--pack <pack_name_or_file>]...

What a reader must not break:
  - Exit code contract for `check`: 2 when at least one requirement is VIOLATED, 0 otherwise,
    and 1 on a usage or input error.
    Why this matters: Automation pipelines rely on exit code 2 to distinguish a breach from a
    clean run (0) or a CLI syntax/file error (1).
  - Only a violation is a breach, so only a violation is non-zero. Unattainable, not applicable
    and not evaluated are findings to read in the report, not verdicts against the system: an
    unattainable requirement says the system as built cannot discharge the duty on the evidence
    supplied, a not-applicable one says the duty is limited to a regulatory class or a decision
    domain this system was not declared to be in, and a not-evaluated one says no engine here
    checked it.
    Why this matters: none of the three is evidence the system failed a duty, so none of them
    fails the caller's build.
  - A run that reported a duty not applicable *only* because the system declared no decision
    domain prints the report's own notice to stderr as well as into the report, and still exits
    on the contract above. Stdout may be JSON, or redirected to a file, or an HTML dossier; a
    caller reading none of those still learns that duties went unchecked for a missing input.
    Why this matters: the exit code cannot distinguish a clean run from a run that looked at
    nothing, so a caller that only watches exit codes must be told some other way.
  - `--capabilities <file>` is the only way a CLI run says the system itself claims the signal
    names: without it the adapter derives capabilities from the trace and the report says so,
    and with it — even an empty or comment-only file, which declares nothing — the report says
    the capabilities were declared by the system's maintainers. The two are distinct claims and
    neither may read as the other.
    Why this matters: trace-derived capability names come from one sample log, while a declared
    set is an authoritative system claim, and a finding must say which one it rests on.
  - `--system-module <module>:<attribute>` imports the named module, which executes it, and takes
    the attribute as the system under test — the `module:attribute` spelling pytest's `-p` and
    gunicorn's application path use. It is the only way a shell run reaches a system that exposes
    `decide()` or `logic()`, and so the only way `probed` and `proved` are reachable without
    writing Python. It must read as a code-loading flag everywhere it is named: `--help` says it
    imports and executes, and so do README and `docs/three-systems.md`.
    Why this matters: a flag that loads and runs the user's code must never read as an innocuous
    file argument.
  - `--system-module` refuses `--system` and `--capabilities`: a decision log names a second,
    different system, and a capability declaration file speaks for that log's adapter, while an
    imported system declares its own capabilities. Neither is merged into the imported system,
    and neither is silently dropped.
    Why this matters: a run that silently ignored one of the two would report on a system the
    caller did not ask about, or on a capability set the system never claimed.
  - `--audience <reader>` selects one of `reasonsmith.render.AUDIENCES` and changes *what the
    text and HTML renderings show*, never what the run claims: one set of verdicts, one set of
    strengths, five artefacts. Omitting it renders the full report, which is byte-for-byte the
    report this CLI printed before the flag existed and is what every generated document under
    `docs/` is pinned to. `--json` is deliberately unprojected: it is the complete machine
    record, and a consumer parsing it must not have fields disappear under a display flag. The
    envelope nonetheless *names* the projection it was asked for in its `audience` block (`null`
    when none was asked for), so a consumer can tell the record it was given from the projection
    the caller requested without a single field being hidden. That envelope names its own shape
    in `schema_version` (`reasonsmith.report.JSON_SCHEMA_VERSION`),
    which is not the package version and moves only when a key is removed, renamed or retyped.
    Why this matters: a reader handed a narrower artefact has been shown less, and must never
    have been told something different — and a reader who reaches for the flag by habit must not
    silently lose fields from a pipeline's JSON.
  - `validate-pack` prints what the pack contains and exits 0, or exits 1 naming the file and
    the requirement at fault for a pack the loader refuses. It reuses the pack loader exactly,
    so the packs a `check` run can load are exactly the packs `validate-pack` accepts.
    Why this matters: the front door must not have a second, looser idea of a valid pack that
    a stranger could validate a pack with and then fail to check against.
  - `validate-pack --analyse` adds `reasonsmith.analysis`'s findings about the pack's formulas —
    joint satisfiability, entailment and equivalence between requirements, vacuous discharge —
    and **does not change the exit code**. A pack the loader accepts is a valid pack; a finding
    is something for its author to read, not a refusal. `--analyse --system-module` imports and
    executes a module exactly as `check --system-module` does, and asks vacuity over that
    system's declared logic as well as reporting a mutation score per duty.
    Why this matters: the exit code means "the loader accepted this pack" and nothing else, so
    a script gating on it does not start failing when an analysis learns to say more. And a flag
    that loads and runs the user's code must read as one wherever it appears.
  - `check --help` ends in worked examples, and the first one is the run that reports a
    *violation* — the reason-deletion certificate against
    `reasonsmith.examples.truncating_credit_system`. Every command there runs after
    `pip install reasonsmith` with no checkout and no data of the reader's own.
    Why this matters: a timed cold read of this project found the tool's strongest result
    reachable from no `--help` string and from none of the shipped examples, so a stranger
    following the tool's own pointing saw only clean runs. The example that fails is the one
    worth showing first.
  - `explain <requirement-id>` prints only fields the pack already carries and, when the record
    is on disk, the fourth column of `docs/refinement.md`. It runs no engine, reads no system and
    changes no verdict. `docs/` is not in the wheel, so an absent record is *named* rather than
    silently dropped, and the command must keep working for a reader who only ran
    `pip install reasonsmith`. It prints no rung ceiling: which rung a duty reaches is decided at
    run time by whichever engine serves it, and a table here would be a hand-maintained claim
    nothing holds to the dispatch.
    Why this matters: the translation from a clause of law to a formula is the one step in this
    tool nothing can verify, so the least it can be is inspectable — and an inspection that
    invented a field would be worse than none.
  - `explain` exits 0 when it printed a requirement and 1 when the id matches nothing or a named
    pack does not load, naming the packs it searched. It never prints an empty frame.
    Why this matters: a reader who mistyped an id must be told what was looked in.

"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any

from reasonsmith import __version__
from reasonsmith.adapters.jsonl import JSONLAdapter
from reasonsmith.render import AUDIENCES
from reasonsmith.report import check_conformance
from reasonsmith.spec import DECISION_DOMAINS, REGULATORY_CLASSES, Pack, list_packs, load_pack
from reasonsmith.sut import SystemUnderTest
from reasonsmith.verdict import Verdict

#: The methods `reasonsmith.sut.SystemUnderTest` requires, in the order a refusal names them.
#: `isinstance` against the runtime-checkable protocol is the gate; this list exists only so the
#: refusal can say *which* method is missing instead of "not a SystemUnderTest".
_SUT_METHODS = ("capabilities", "decisions", "logic")


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


def load_system_module(spec: str) -> Any:
    """Import `module:attribute` and return the system under test it names.

    Importing a module executes it — that is what this function is for, and every message it
    raises names the module path it was told to load, so a reader at 2am can see what ran.

    The attribute may be either a `SystemUnderTest` instance or a zero-argument factory returning
    one; the example systems in `reasonsmith.examples` expose a `system_under_test()` factory. An
    object that already satisfies the protocol is taken as-is and never called, so an adapter that
    also happens to be callable is not mistaken for its own factory.
    """
    module_name, separator, attribute_name = spec.rpartition(":")
    if not separator or not module_name or not attribute_name:
        raise ValueError(
            f"--system-module {spec!r}: expected 'module:attribute', for example "
            "'reasonsmith.examples.symbolic_rules:system_under_test'. The part before the colon "
            "is an importable module path (dots, not slashes, and no '.py'), the part after it is "
            "the "
            "name of a SystemUnderTest or of a factory returning one."
        )

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        raise ValueError(
            f"--system-module {spec!r}: importing module {module_name!r} failed with "
            f"{type(exc).__name__}: {exc}. Importing a module runs it, so this is either the "
            "module not being found on sys.path (which includes the current directory) or "
            "an error raised while it executed."
        ) from exc

    try:
        obj = getattr(module, attribute_name)
    except AttributeError as exc:
        raise ValueError(
            f"--system-module {spec!r}: module {module_name!r} imported, but has no attribute "
            f"{attribute_name!r} (loaded from {getattr(module, '__file__', 'an unknown file')!r})."
        ) from exc

    if not isinstance(obj, SystemUnderTest) and callable(obj):
        try:
            obj = obj()
        except Exception as exc:
            raise ValueError(
                f"--system-module {spec!r}: calling {module_name}.{attribute_name}() raised "
                f"{type(exc).__name__}: {exc}"
            ) from exc

    if not isinstance(obj, SystemUnderTest):
        missing = [name for name in _SUT_METHODS if not callable(getattr(obj, name, None))]
        raise ValueError(
            f"--system-module {spec!r}: {module_name}.{attribute_name} is a "
            f"{type(obj).__name__}, which is not a reasonsmith.sut.SystemUnderTest: it is missing "
            f"{', '.join(missing)}. A system under test must define "
            f"{', '.join(f'{name}()' for name in _SUT_METHODS)}."
        )
    return obj


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
            f"| binding: {str(req.binding).lower()} | scope: {req.scope or 'unset'} "
            f"| domains: {', '.join(req.domains) or 'none'}"
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
            "     malformed capability declaration, a --system-scope that is not a known\n"
            "     regulatory class, a --system-domain that is not a known decision domain,\n"
            "     no system given, --system-module combined with --system or\n"
            "     --capabilities, or a --system-module that does not import, names no such\n"
            "     attribute, or is not a SystemUnderTest).\n"
            "exit codes for validate-pack:\n"
            "  0  every pack loaded and printed. --analyse findings do not change this: a\n"
            "     pack the loader accepts is a valid pack, and a finding is for its author.\n"
            "  1  a pack the loader refuses, naming the file and the requirement at fault, or\n"
            "     a --system-module that does not import, names no such attribute, is not a\n"
            "     SystemUnderTest, or was given without --analyse.\n"
            "exit codes for explain:\n"
            "  0  the requirement was found and printed.\n"
            "  1  no pack searched ships that requirement id, or a named pack does not load."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"reasonsmith {__version__}",
        help="Print the installed version and exit",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    check_parser = subparsers.add_parser(
        "check",
        help="Check SUT conformance against a pack",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "worked examples, all shipped inside the package and runnable after\n"
            "`pip install reasonsmith`, with no checkout and no data of your own:\n"
            "\n"
            "  the reason-deletion certificate — a credit system whose notice states one reason\n"
            "  while its own inference used five. This run reports VIOLATED and names the four\n"
            "  reasons it deleted, measured by re-running that inference:\n"
            "    reasonsmith check --system-module "
            "reasonsmith.examples.truncating_credit_system:system_under_test --pack ecoa\n"
            "\n"
            "  the same three systems the README's table compares, one duty at three rungs:\n"
            "    reasonsmith check --system-module "
            "reasonsmith.examples.neural_scorer:system_under_test --pack ecoa\n"
            "    reasonsmith check --system-module "
            "reasonsmith.examples.probabilistic_scorer:system_under_test --pack ecoa\n"
            "    reasonsmith check --system-module "
            "reasonsmith.examples.symbolic_rules:system_under_test --pack ecoa\n"
            "\n"
            "  a plain decision log, which cannot rise above the observed rung:\n"
            "    reasonsmith check --system "
            '"$(python -m reasonsmith.examples)/sample_decisions.jsonl" --pack ecoa '
            "--system-domain consumer-credit\n"
        ),
    )
    check_parser.add_argument(
        "--system",
        "-s",
        default=None,
        help="Path to JSONL decision log file or system specification",
    )
    check_parser.add_argument(
        "--system-module",
        default=None,
        metavar="MODULE:ATTRIBUTE",
        help=(
            "IMPORTS AND EXECUTES the named Python module, and takes ATTRIBUTE from it as the "
            "system under test — the same module:attribute loading pytest's -p and gunicorn's "
            "application path do. The module is searched on sys.path, which includes the current "
            "directory, so an installed module and one in the working directory both resolve. "
            "ATTRIBUTE may be a SystemUnderTest or a zero-argument factory returning one, e.g. "
            "'reasonsmith.examples.symbolic_rules:system_under_test' (shipped in the package). "
            "A system imported this way can "
            "expose decide() and logic(), so it reaches the probed and proved rungs a decision "
            "log cannot. Mutually exclusive with --system and --capabilities"
        ),
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
        "--system-domain",
        action="append",
        default=None,
        dest="system_domains",
        metavar="DOMAIN",
        help=(
            "Declared decision domain of the system — the kind of decision it makes — one of: "
            f"{', '.join(DECISION_DOMAINS)}. Repeat the flag for a system that makes more than "
            "one kind. Requirements about other domains, or about any domain when this is left "
            "undeclared, are reported not applicable rather than assumed to apply. This "
            "vocabulary is the pack author's, not any regulation's; a value outside it is a "
            "usage error rather than a clean run"
        ),
    )
    check_parser.add_argument(
        "--audience",
        default=None,
        choices=sorted(AUDIENCES),
        help=(
            "Project the text and HTML renderings for one reader. The run, the verdicts and the "
            "strengths are the same whichever is given — only what is shown changes, and every "
            "audience keeps the limits of the report. Omitted, the full report is printed, which "
            "is what the auditor projection also gives. --json is not projected and never loses "
            "a field to this flag; it only *names* the projection asked for, in its `audience` "
            "block, so a machine consumer can tell the record from the display it was built for. "
            "docs/semantics.md names what each shows"
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
    validate_parser.add_argument(
        "--analyse",
        "--analyze",
        action="store_true",
        dest="analyse",
        help=(
            "Also analyse the pack as a set of formulas: whether its requirements are jointly "
            "satisfiable, which of them entail or are equivalent to which, and which are "
            "vacuously discharged. Findings are printed and do not change the exit code — a "
            "pack with findings is still a pack the loader accepts"
        ),
    )
    validate_parser.add_argument(
        "--system-module",
        default=None,
        metavar="MODULE:ATTRIBUTE",
        help=(
            "With --analyse: IMPORTS AND EXECUTES the named Python module and takes ATTRIBUTE "
            "from it as the system under test, exactly as `check --system-module` does. Vacuity "
            "is then asked over the inputs that system's declared logic and constraints admit "
            "rather than over every assignment to the signals, and a mutation score per duty is "
            "reported — which reaches only a system exposing its rules through logic()"
        ),
    )

    metrics_parser = subparsers.add_parser(
        "published-counts",
        help="Emit machine-readable counts and provenance for the site build",
    )
    metrics_parser.add_argument(
        "--output", "-o", default="-", help="Write JSON to FILE (default: stdout)",
    )

    explain_parser = subparsers.add_parser(
        "explain",
        help="Print how one requirement's clause of law became its formula",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "example:\n"
            "  reasonsmith explain ecoa_reg_b_1002_9_b_2_specific_reasons\n"
            "\n"
            "Every line printed is a field of the pack, or a cell of docs/refinement.md when\n"
            "that record is on disk — it is not packaged in the wheel, and its absence is said\n"
            "rather than hidden. No rung is printed: which rung a duty reaches is decided by\n"
            "whichever engine serves it at run time, not by its fragment.\n"
        ),
    )
    explain_parser.add_argument(
        "requirement_id",
        help="Requirement id, e.g. ecoa_reg_b_1002_9_b_2_specific_reasons",
    )
    explain_parser.add_argument(
        "--pack",
        "-p",
        action="append",
        default=None,
        dest="packs",
        help=(
            "Pack name or TOML file path to search; repeat for several. Omitted, every built-in "
            f"pack is searched: {', '.join(list_packs())}"
        ),
    )

    parsed = parser.parse_args(args)

    if parsed.command == "published-counts":
        from reasonsmith.published_counts import published_counts

        try:
            payload = json.dumps(published_counts(), indent=2) + "\n"
        except ValueError as exc:
            print(f"Error computing published counts: {exc}", file=sys.stderr)
            return 1
        if parsed.output == "-":
            print(payload, end="")
        else:
            try:
                with open(parsed.output, "w", encoding="utf-8") as handle:
                    handle.write(payload)
            except OSError as exc:
                print(f"Error writing published counts {parsed.output!r}: {exc}", file=sys.stderr)
                return 1
        return 0

    if parsed.command == "explain":
        from reasonsmith.explain import find_requirement, refinement_notes, render_explanation

        try:
            req, pack_id = find_requirement(parsed.requirement_id, parsed.packs)
        except LookupError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"Error loading pack: {exc}", file=sys.stderr)
            return 1
        print(render_explanation(req, pack_id, refinement_notes()))
        return 0

    if parsed.command == "validate-pack":
        if parsed.system_module is not None and not parsed.analyse:
            print(
                f"Error: --system-module '{parsed.system_module}' imports and runs a system, "
                "which validate-pack has nothing to do with unless --analyse is also given. Add "
                "--analyse, or drop --system-module.",
                file=sys.stderr,
            )
            return 1
        analysis_sut = None
        if parsed.system_module is not None:
            cwd = os.getcwd()
            if cwd not in sys.path:
                sys.path.insert(0, cwd)
            try:
                analysis_sut = load_system_module(parsed.system_module)
            except ValueError as exc:
                print(f"Error: {exc}", file=sys.stderr)
                return 1
        for name in parsed.pack:
            try:
                pack = load_pack(name)
            except Exception as exc:
                print(f"Error validating pack {name!r}: {exc}", file=sys.stderr)
                return 1
            print(format_pack(pack))
            if parsed.analyse:
                from reasonsmith.analysis import analyse_pack, render_analysis

                print(render_analysis(analyse_pack(pack, analysis_sut)))
        return 0

    if parsed.command == "check":
        if parsed.system is None and parsed.system_module is None:
            print(
                "Error: give a system to check — either --system <decisions.jsonl> (a decision "
                "log) or --system-module <module>:<attribute> (imports and executes the module).",
                file=sys.stderr,
            )
            return 1
        if parsed.system is not None and parsed.system_module is not None:
            # Paths are quoted plainly, never through repr: on Windows repr doubles every
            # backslash, so a reader is shown a path they did not type and cannot paste back.
            print(
                f"Error: --system '{parsed.system}' and --system-module "
                f"'{parsed.system_module}' name two different systems: one a decision log, the "
                "other a module to import and run. Nothing here merges them. Give one.",
                file=sys.stderr,
            )
            return 1
        if parsed.system_module is not None and parsed.capabilities is not None:
            print(
                f"Error: --capabilities '{parsed.capabilities}' declares the signals for a "
                "decision log's adapter, but --system-module imports a system that declares its "
                "own capabilities. Nothing here overrides those. Drop --capabilities.",
                file=sys.stderr,
            )
            return 1

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

        if parsed.system_module is not None:
            # The module path is resolved from the caller's working directory, the way pytest and
            # gunicorn resolve theirs; a console script's sys.path does not carry it.
            cwd = os.getcwd()
            if cwd not in sys.path:
                sys.path.insert(0, cwd)
            try:
                sut = load_system_module(parsed.system_module)
            except ValueError as exc:
                print(f"Error: {exc}", file=sys.stderr)
                return 1
        else:
            try:
                sut = JSONLAdapter(
                    parsed.system, declared_capabilities=declared_capabilities
                )
            except Exception as exc:
                print(f"Error loading system log {parsed.system!r}: {exc}", file=sys.stderr)
                return 1

        try:
            report = check_conformance(
                sut,
                pack,
                system_name=parsed.system_name,
                system_scope=parsed.system_scope,
                system_domains=parsed.system_domains,
            )
        except (TypeError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        notice = report.undeclared_domain_notice
        if notice:
            print(f"Warning: {notice}", file=sys.stderr)

        if parsed.html:
            cmd_args = args if args is not None else sys.argv[1:]
            if args is not None or __name__ == "__main__":
                command = ["python", "-m", "reasonsmith.cli", *cmd_args]
            else:
                command = [sys.argv[0], *cmd_args]
            cmd_str = shlex.join(command)
            html_content = report.render_html(command=cmd_str, audience=parsed.audience)
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
                print(
                    report.to_json(indent=2, audience=parsed.audience)
                    if parsed.json
                    else report.render_text(audience=parsed.audience)
                )
        elif parsed.json:
            print(report.to_json(indent=2, audience=parsed.audience))
        else:
            print(report.render_text(audience=parsed.audience))

        violations = [r for r in report.results if r.verdict == Verdict.VIOLATED]
        return 2 if violations else 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
