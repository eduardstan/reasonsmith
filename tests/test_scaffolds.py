from __future__ import annotations

import tomllib

import pytest

import reasonsmith.plugins as plugins
from reasonsmith.cli import load_system_module, main
from reasonsmith.report import RequirementResult
from reasonsmith.scaffold import ScaffoldError, create_scaffold
from reasonsmith.spec import (
    Pack,
    load_pack,
    normalize_claimed_semantics,
    normalize_domain,
    normalize_domains,
)
from reasonsmith.verdict import Strength, Verdict


def test_init_pack_creates_loadable_entry_point_package(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "pack", "my-pack"]) == 0
    output = capsys.readouterr().out
    assert "Created pack scaffold" in output
    root = tmp_path / "my-pack"
    metadata = tomllib.loads((root / "pyproject.toml").read_text())
    assert metadata["project"]["entry-points"]["reasonsmith.packs"]["my-pack"] == (
        "my_pack:pack_path"
    )
    pack = load_pack(root / "src" / "my_pack" / "pack.toml")
    assert pack.id == "my_pack"
    assert "TODO" in (root / "README.md").read_text()


def test_init_engine_creates_declining_engine_scaffold(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "engine", "my-engine"]) == 0
    capsys.readouterr()
    root = tmp_path / "my-engine"
    metadata = tomllib.loads((root / "pyproject.toml").read_text())
    assert metadata["project"]["entry-points"]["reasonsmith.engines"]["my-engine"] == (
        "my_engine:engine"
    )
    source = (root / "src" / "my_engine" / "engine.py").read_text()
    assert "max_strength = Strength.OBSERVED.value" in source
    assert "docs/authoring-engines.md" in source
    assert "verify-engine" in (root / "README.md").read_text()


def test_scaffold_refuses_invalid_or_existing_names(tmp_path):
    with pytest.raises(ScaffoldError):
        create_scaffold("pack", "../escape", tmp_path)
    create_scaffold("pack", "already", tmp_path)
    with pytest.raises(ScaffoldError):
        create_scaffold("pack", "already", tmp_path)


def test_scaffold_reports_unknown_kind_and_cleans_up_write_failure(tmp_path, monkeypatch):
    with pytest.raises(ScaffoldError):
        create_scaffold("other", "name", tmp_path)

    def fail_write(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(type(tmp_path / "x"), "write_text", fail_write)
    with pytest.raises(OSError):
        create_scaffold("pack", "broken", tmp_path)
    assert not (tmp_path / "broken").exists()


def test_init_cli_reports_collision(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["init", "pack", "duplicate"]) == 0
    assert main(["init", "pack", "duplicate"]) == 1
    assert "Error creating pack scaffold" in capsys.readouterr().err


def test_cli_and_loader_report_extension_errors(tmp_path, monkeypatch, capsys):
    bad = tmp_path / "bad_factory.py"
    bad.write_text("def make():\n    raise RuntimeError('nope')\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    with pytest.raises(ValueError, match="calling"):
        load_system_module("bad_factory:make")

    assert main(["published-counts", "--output", str(tmp_path)]) == 1
    assert main(["published-counts", "--output", str(tmp_path / "counts.json")]) == 0
    assert main(["check", "--system", str(tmp_path / "missing.jsonl"), "--pack", "missing"]) == 1
    assert main(["validate-pack", "--analyse", "--system-module", "bad_factory:make", "ecoa"]) == 1
    captured = capsys.readouterr()
    assert "Error" in captured.err


def test_extension_and_spec_boundary_errors(monkeypatch):
    with pytest.raises(TypeError):
        normalize_claimed_semantics(1)
    with pytest.raises(TypeError):
        normalize_domain(1)
    with pytest.raises(TypeError):
        normalize_domains(1)
    with pytest.raises(ValueError, match="contains no requirements"):
        Pack(id="empty", title="empty", description="empty", requirements=())

    monkeypatch.setattr(plugins, "discover", lambda group, builtin_names=(): [("other", object())])
    assert plugins.pack_path("wanted") is None
    monkeypatch.setattr(plugins, "discover", lambda group, builtin_names=(): [("wanted", 1)])
    with pytest.raises(ValueError, match="must resolve to a path"):
        plugins.pack_path("wanted")
    # An absent packs directory is a valid empty installation state.
    from reasonsmith import spec

    class MissingDirectory:
        def exists(self):
            return False

    monkeypatch.setattr(spec, "PACKS_DIR", MissingDirectory())
    assert spec.list_packs() == []


def test_plugin_wrong_requirement_id_is_refused():
    class WrongEngine:
        def evaluate(self, req, sut, records):
            return RequirementResult(
                requirement_id="different",
                source_clause="Doc Art. 1",
                verdict=Verdict.INCONCLUSIVE,
                strength=None,
                signals_required=("signal_a",),
            )

    req = type("Req", (), {
        "id": "wanted",
        "source_document": "Doc",
        "article_clause": "Art. 1",
        "requires": ("signal_a",),
        "binding": True,
        "scope": "",
    })()
    result = plugins._run(req, object(), lambda: [], "wrong", WrongEngine(), Strength.OBSERVED)
    assert result.verdict is Verdict.INCONCLUSIVE
