"""Tests for the v1 launch surface: console entry point, capability declarations, validate-pack.

Covers:
- `[project.scripts]` entry point metadata, keeping `python -m reasonsmith.cli` working
- `--capabilities <file>`: declared basis end to end, trace basis without it (no behaviour
  change), and malformed declarations rejected naming the file and the line
- `validate-pack`: accepts every shipped pack and prints what it contains; rejects a broken
  pack naming the file and the requirement id at fault
- `--system-module module:attribute`: the two shipped adapters that expose `decide()` and
  `logic()` reaching `probed` and `proved` from the CLI, and every refusal the flag makes
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

import pytest

from reasonsmith.adapters import JSONLAdapter
from reasonsmith.cli import main as cli_main
from reasonsmith.cli import read_capability_declaration
from reasonsmith.spec import list_packs, load_pack


@pytest.fixture
def jsonl_fixture_file(tmp_path: Path) -> Path:
    """Fixture JSONL file whose trace lacks the signals two ecoa requirements need.

    The trace carries everything the record-formalism requirement needs, but no
    `artifact_logs_counteroffer_not_accepted` (needed by the timing requirement) and no
    `scope_statements_local_vs_global` (needed by the specific-reasons requirement), so the
    report always has an unattainable finding whose wording names the capability basis.
    """
    log_file = tmp_path / "decisions.jsonl"
    records = [
        {
            "artifact_logs_decision_record": {"id": "dec-1", "result": "approved"},
            "artifact_logs_notification_latency_days": 12,
            "artifact_logs_reason_explanation": "Credit score 750 exceeds threshold",
            "provenance_model_version": "v1.2.0",
            "artifact_logs_event_log": True,
        },
        {
            "artifact_logs_decision_record": {"id": "dec-2", "result": "approved"},
            "artifact_logs_notification_latency_days": 15,
            "artifact_logs_reason_explanation": "Debt-to-income ratio 0.45 exceeds 0.36 limit",
            "provenance_model_version": "v1.2.0",
            "artifact_logs_event_log": True,
        },
    ]
    log_file.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )
    return log_file


@pytest.fixture
def write_module(tmp_path: Path, monkeypatch):
    """Write a throwaway importable module and return its module name.

    `--system-module` imports whatever it is named, so the refusal tests need modules that fail
    in specific ways. Each gets a unique name, since a module imported once stays imported.
    """
    monkeypatch.syspath_prepend(str(tmp_path))

    def write(name: str, source: str) -> str:
        (tmp_path / f"{name}.py").write_text(source, encoding="utf-8")
        return name

    return write


TRACE_ONLY_SIGNALS = [
    "artifact_logs_decision_record",
    "artifact_logs_notification_latency_days",
    "artifact_logs_reason_explanation",
    "provenance_model_version",
    "artifact_logs_event_log",
]


class TestConsoleEntryPoint:
    def test_pyproject_declares_the_reasonsmith_console_script(self, capsys):
        data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        assert data["project"]["scripts"]["reasonsmith"] == "reasonsmith.cli:main"

        assert cli_main([]) == 1
        assert "usage" in capsys.readouterr().out.lower()

    def test_html_provenance_distinguishes_console_and_module_invocations(
        self, jsonl_fixture_file: Path, monkeypatch, tmp_path: Path
    ):
        module_report = tmp_path / "module.html"
        command_args = [
            "check",
            "--system",
            str(jsonl_fixture_file),
            "--pack",
            "ecoa",
            "--html",
            str(module_report),
        ]
        assert cli_main(command_args) == 0
        assert "Command: <code>python -m reasonsmith.cli check" in module_report.read_text(
            encoding="utf-8"
        )

        console_report = tmp_path / "console.html"
        command_args[-1] = str(console_report)
        monkeypatch.setattr("sys.argv", ["reasonsmith", *command_args])
        assert cli_main() == 0
        console_html = console_report.read_text(encoding="utf-8")
        assert "Command: <code>reasonsmith check" in console_html
        assert "python -m reasonsmith.cli" not in console_html


class TestCapabilityDeclaration:
    def test_reads_one_name_per_line_ignoring_comments_and_blanks(self, tmp_path: Path):
        caps = tmp_path / "caps.txt"
        caps.write_text(
            "# what this system can emit\n"
            "artifact_logs_decision_record\n"
            "\n"
            "provenance_model_version\n",
            encoding="utf-8",
        )
        assert read_capability_declaration(str(caps)) == {
            "artifact_logs_decision_record",
            "provenance_model_version",
        }

    def test_empty_or_comment_only_file_declares_nothing(self, tmp_path: Path):
        empty = tmp_path / "empty.txt"
        empty.write_text("", encoding="utf-8")
        assert read_capability_declaration(str(empty)) == set()
        comments = tmp_path / "comments.txt"
        comments.write_text("# nothing declared\n\n# still nothing\n", encoding="utf-8")
        assert read_capability_declaration(str(comments)) == set()

    def test_comma_and_whitespace_lines_are_refused_by_file_and_line(self, tmp_path: Path):
        caps = tmp_path / "caps.txt"
        caps.write_text("artifact_logs_decision_record\na b\n", encoding="utf-8")
        with pytest.raises(ValueError) as excinfo:
            read_capability_declaration(str(caps))
        message = str(excinfo.value)
        assert str(caps) in message
        assert "line 2" in message
        assert "'a b'" in message

        caps.write_text("a, b\n", encoding="utf-8")
        with pytest.raises(ValueError) as excinfo:
            read_capability_declaration(str(caps))
        message = str(excinfo.value)
        assert str(caps) in message
        assert "line 1" in message
        assert "comma" in message

    def test_missing_file_is_refused(self, tmp_path: Path):
        with pytest.raises(ValueError, match="Cannot read capability declaration file"):
            read_capability_declaration(str(tmp_path / "no_such.txt"))

    def test_adapter_basis_reflects_declaration(self, jsonl_fixture_file: Path, tmp_path: Path):
        sut = JSONLAdapter(str(jsonl_fixture_file))
        assert sut.capability_basis == "trace"
        assert sut.capabilities() == set(TRACE_ONLY_SIGNALS)

        caps = tmp_path / "caps.txt"
        caps.write_text("artifact_logs_decision_record\n", encoding="utf-8")
        declared = JSONLAdapter(
            str(jsonl_fixture_file),
            declared_capabilities=read_capability_declaration(str(caps)),
        )
        assert declared.capability_basis == "declared"
        assert declared.capabilities() == {"artifact_logs_decision_record"}

        empty = tmp_path / "empty.txt"
        empty.write_text("", encoding="utf-8")
        nothing = JSONLAdapter(
            str(jsonl_fixture_file),
            declared_capabilities=read_capability_declaration(str(empty)),
        )
        assert nothing.capability_basis == "declared"
        assert nothing.capabilities() == set()

    def test_no_declaration_keeps_trace_derived_basis(self, jsonl_fixture_file: Path, capsys):
        """Without --capabilities the CLI must behave exactly as before: derive from the trace."""
        rc = cli_main(["check", "--system", str(jsonl_fixture_file), "--pack", "ecoa"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Unattainable on the evidence supplied" in captured.out
        assert "and the system declared no capabilities" in captured.out

    def test_empty_declaration_file_declares_nothing(
        self, jsonl_fixture_file: Path, capsys, tmp_path
    ):
        caps = tmp_path / "caps.txt"
        caps.write_text("# declares nothing\n\n", encoding="utf-8")
        rc = cli_main(
            [
                "check",
                "--system",
                str(jsonl_fixture_file),
                "--pack",
                "ecoa",
                "--capabilities",
                str(caps),
            ]
        )
        assert rc == 0
        captured = capsys.readouterr()
        assert "Unattainable as built" in captured.out
        assert "Determined from declared capabilities alone; the system was not executed" in (
            captured.out
        )

    def test_declared_capabilities_are_worded_as_declared(
        self, jsonl_fixture_file: Path, capsys, tmp_path
    ):
        caps = tmp_path / "caps.txt"
        caps.write_text("\n".join(TRACE_ONLY_SIGNALS) + "\n", encoding="utf-8")
        rc = cli_main(
            [
                "check",
                "--system",
                str(jsonl_fixture_file),
                "--pack",
                "ecoa",
                "--capabilities",
                str(caps),
            ]
        )
        assert rc == 0
        captured = capsys.readouterr()
        assert "Unattainable as built" in captured.out
        assert "the system was not executed" in captured.out

    def test_malformed_declaration_is_a_usage_error_naming_file_and_line(
        self, jsonl_fixture_file: Path, capsys, tmp_path
    ):
        caps = tmp_path / "caps.txt"
        caps.write_text(
            "artifact_logs_decision_record\n"
            "artifact_logs_decision_record, provenance_model_version\n",
            encoding="utf-8",
        )
        rc = cli_main(
            [
                "check",
                "--system",
                str(jsonl_fixture_file),
                "--pack",
                "ecoa",
                "--capabilities",
                str(caps),
            ]
        )
        assert rc == 1
        captured = capsys.readouterr()
        assert "CONFORMANCE REPORT" not in captured.out
        assert str(caps) in captured.err
        assert "line 2" in captured.err

    def test_missing_declaration_file_is_a_usage_error(
        self, jsonl_fixture_file: Path, capsys, tmp_path
    ):
        rc = cli_main(
            [
                "check",
                "--system",
                str(jsonl_fixture_file),
                "--pack",
                "ecoa",
                "--capabilities",
                str(tmp_path / "no_such.txt"),
            ]
        )
        assert rc == 1
        captured = capsys.readouterr()
        assert "capability declaration" in captured.err

        rc = cli_main(
            [
                "check",
                "--system",
                str(jsonl_fixture_file),
                "--pack",
                "ecoa",
                "--capabilities",
                "",
            ]
        )
        assert rc == 1
        captured = capsys.readouterr()
        assert "capability declaration ''" in captured.err


class TestSystemModule:
    """`--system-module module:attribute`: the shell's way to a system, not just a log file.

    The two rungs a decision log cannot reach — `probed` and `proved` — are reachable from a
    shell exactly when the imported system exposes `decide()` or `logic()`, so the two shipped
    adapters that do are checked end to end here. Every refusal exits 1 and names what is wrong.
    """

    def test_symbolic_adapter_reaches_proved(self, capsys):
        rc = cli_main(
            [
                "check",
                "--system-module",
                "docs.adapters.symbolic_rules:system_under_test",
                "--pack",
                "ecoa",
            ]
        )
        assert rc == 0
        assert "[PROVED] ecoa_reg_b_1002_9_b_2_specific_reasons" in capsys.readouterr().out

    def test_probabilistic_adapter_reaches_probed(self, capsys):
        rc = cli_main(
            [
                "check",
                "--system-module",
                "docs.adapters.probabilistic_scorer:system_under_test",
                "--pack",
                "ecoa",
            ]
        )
        assert rc == 0
        out = capsys.readouterr().out
        assert "[PROBED] ecoa_reg_b_1002_9_b_2_specific_reasons" in out
        assert "probe budget:" in out

    def test_an_instance_attribute_is_accepted_without_being_called(self, capsys, write_module):
        """An already-built SystemUnderTest is taken as-is; only a non-SUT callable is called."""
        module = write_module(
            "instance_system",
            "from docs.adapters.symbolic_rules import system_under_test\n"
            "system = system_under_test()\n",
        )
        rc = cli_main(["check", "--system-module", f"{module}:system", "--pack", "ecoa"])
        assert rc == 0
        assert "[PROVED] ecoa_reg_b_1002_9_b_2_specific_reasons" in capsys.readouterr().out

    def test_a_module_that_does_not_import_names_the_module(self, capsys, write_module):
        module = write_module("broken_system", "raise RuntimeError('boom')\n")
        rc = cli_main(["check", "--system-module", f"{module}:system", "--pack", "ecoa"])
        assert rc == 1
        err = capsys.readouterr().err
        assert module in err
        assert "RuntimeError: boom" in err

        rc = cli_main(["check", "--system-module", "no_such_module:system", "--pack", "ecoa"])
        assert rc == 1
        assert "no_such_module" in capsys.readouterr().err

    def test_a_missing_attribute_names_attribute_and_module(self, capsys):
        rc = cli_main(
            [
                "check",
                "--system-module",
                "docs.adapters.symbolic_rules:no_such_attribute",
                "--pack",
                "ecoa",
            ]
        )
        assert rc == 1
        err = capsys.readouterr().err
        assert "'no_such_attribute'" in err
        assert "docs.adapters.symbolic_rules" in err

    def test_a_non_sut_object_names_the_missing_protocol_method(self, capsys, write_module):
        module = write_module(
            "half_a_system",
            "class HalfASystem:\n"
            "    def capabilities(self):\n"
            "        return set()\n"
            "    def decisions(self):\n"
            "        return []\n"
            "system = HalfASystem()\n",
        )
        rc = cli_main(["check", "--system-module", f"{module}:system", "--pack", "ecoa"])
        assert rc == 1
        err = capsys.readouterr().err
        assert "HalfASystem" in err
        assert "missing logic" in err

    def test_a_spec_without_a_colon_is_refused(self, capsys):
        rc = cli_main(
            ["check", "--system-module", "docs.adapters.symbolic_rules", "--pack", "ecoa"]
        )
        assert rc == 1
        assert "module:attribute" in capsys.readouterr().err

    def test_a_decisions_file_and_a_module_are_a_contradiction(
        self, jsonl_fixture_file: Path, capsys
    ):
        rc = cli_main(
            [
                "check",
                "--system",
                str(jsonl_fixture_file),
                "--system-module",
                "docs.adapters.symbolic_rules:system_under_test",
                "--pack",
                "ecoa",
            ]
        )
        assert rc == 1
        err = capsys.readouterr().err
        assert str(jsonl_fixture_file) in err
        assert "two different systems" in err

    def test_a_capability_declaration_and_a_module_are_a_contradiction(self, capsys, tmp_path):
        caps = tmp_path / "caps.txt"
        caps.write_text("provenance_model_version\n", encoding="utf-8")
        rc = cli_main(
            [
                "check",
                "--system-module",
                "docs.adapters.symbolic_rules:system_under_test",
                "--capabilities",
                str(caps),
                "--pack",
                "ecoa",
            ]
        )
        assert rc == 1
        assert "declares its own capabilities" in capsys.readouterr().err

    def test_no_system_at_all_is_a_usage_error(self, capsys):
        rc = cli_main(["check", "--pack", "ecoa"])
        assert rc == 1
        assert "--system-module" in capsys.readouterr().err

    def test_help_says_the_flag_imports_and_executes(self, capsys):
        with pytest.raises(SystemExit):
            cli_main(["check", "--help"])
        assert "IMPORTS AND EXECUTES the named Python module" in " ".join(
            capsys.readouterr().out.split()
        )


class TestValidatePack:
    def test_accepts_every_shipped_pack(self, capsys):
        rc = cli_main(["validate-pack", *list_packs()])
        assert rc == 0
        captured = capsys.readouterr()
        for name in list_packs():
            assert f"pack: {name}" in captured.out

    def test_prints_what_a_pack_contains(self, capsys):
        rc = cli_main(["validate-pack", "ecoa"])
        assert rc == 0
        captured = capsys.readouterr()
        pack = load_pack("ecoa")
        assert "pack: ecoa" in captured.out
        assert "source.document" in captured.out
        assert f"requirements: {len(pack.requirements)}" in captured.out
        for req in pack.requirements:
            assert req.id in captured.out
            assert req.article_clause in captured.out

    def test_rejects_a_broken_pack_naming_file_and_requirement(self, tmp_path: Path, capsys):
        broken = tmp_path / "broken.toml"
        broken.write_text('[[requirement]]\nid = "broken_req"\n', encoding="utf-8")
        rc = cli_main(["validate-pack", str(broken)])
        assert rc == 1
        captured = capsys.readouterr()
        assert str(broken) in captured.err
        assert "broken_req" in captured.err

    def test_rejects_an_unknown_pack_name(self, capsys):
        rc = cli_main(["validate-pack", "no_such_pack"])
        assert rc == 1
        captured = capsys.readouterr()
        assert "no_such_pack" in captured.err
