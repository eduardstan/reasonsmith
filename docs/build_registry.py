"""Build the static discovery registry page.

Run with ``python docs/build_registry.py``. The page is an inventory, not a
service: it records what the local Python environment exposes through the
reasonsmith entry-point groups.
"""
# ruff: noqa: E501

from __future__ import annotations

import html
import importlib.metadata
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from reasonsmith.plugins import (  # noqa: E402
    BUILTIN_ENGINE_NAMES,
    ENGINE_GROUP,
    PACK_GROUP,
)
from reasonsmith.spec import list_packs, load_pack  # noqa: E402
from reasonsmith.verdict import Strength  # noqa: E402

BUILD_COMMAND = "python docs/build_registry.py"
REGISTRY_HTML = ROOT / "docs" / "registry.html"
DISCLAIMER = (
    "discovery is the source, and the page is not an endorsement or an audit of a listed package."
)
# The ceiling of each in-tree engine is the rung at which report.py places it.
BUILTIN_CEILINGS = {
    "record": Strength.OBSERVED,
    "observed": Strength.OBSERVED,
    "probed": Strength.PROBED,
    "proved": Strength.PROVED,
    "certificate": Strength.PROBED,
    "temporal": Strength.PROVED,
    "counterfactual": Strength.PROBED,
}


def _entry_points(group: str) -> list[Any]:
    eps = importlib.metadata.entry_points()
    selected = eps.select(group=group) if hasattr(eps, "select") else eps.get(group, ())
    return sorted(selected, key=lambda ep: ep.name)


def _origin(ep: Any) -> str:
    dist = getattr(ep, "dist", None)
    return f"installed package: {dist.name}" if dist is not None else "installed package"


def _verify(name: str) -> str:
    """Run the local verify-engine kit, retaining only its pass/fail result."""
    try:
        from reasonsmith.verify_engine import verify_engine

        rows, _ = verify_engine(name)
        return "passed" if all(row.passed for row in rows) else "failed"
    except Exception as exc:  # a registry must remain buildable with broken third parties
        return f"not verified ({type(exc).__name__})"


def _pack_rows() -> list[dict[str, str]]:
    rows = []
    for name in list_packs():
        pack = load_pack(name)
        counts = Counter(req.formalism for req in pack.requirements)
        split = ", ".join(f"{key}: {counts[key]}" for key in sorted(counts))
        rows.append(
            {
                "name": name,
                "origin": "built-in (reasonsmith)",
                "duties": str(len(pack.requirements)),
                "formalism": split,
            }
        )
    for ep in _entry_points(PACK_GROUP):
        if ep.name in list_packs():
            continue
        try:
            value = ep.load()
            value = value() if callable(value) else value
            pack = load_pack(value)
            counts = Counter(req.formalism for req in pack.requirements)
            split = ", ".join(f"{key}: {counts[key]}" for key in sorted(counts))
            rows.append(
                {
                    "name": ep.name,
                    "origin": _origin(ep),
                    "duties": str(len(pack.requirements)),
                    "formalism": split,
                }
            )
        except Exception:
            rows.append(
                {
                    "name": ep.name,
                    "origin": _origin(ep),
                    "duties": "not validated",
                    "formalism": "not validated",
                }
            )
    return rows


def _engine_rows() -> list[dict[str, str]]:
    rows = [
        {
            "name": n,
            "origin": "built-in (reasonsmith)",
            "ceiling": c.value,
            "verified": "not verified",
        }
        for n, c in BUILTIN_CEILINGS.items()
    ]
    for ep in _entry_points(ENGINE_GROUP):
        if ep.name in BUILTIN_ENGINE_NAMES:
            continue
        try:
            engine = ep.load()
            ceiling = Strength.parse(engine.max_strength).value
            verified = _verify(ep.name)
        except Exception:
            ceiling, verified = "not declared", "not verified"
        rows.append(
            {"name": ep.name, "origin": _origin(ep), "ceiling": ceiling, "verified": verified}
        )
    return rows


def _cell(value: str) -> str:
    return f"<td>{html.escape(value)}</td>"


def build() -> str:
    packs, engines = _pack_rows(), _engine_rows()
    pack_html = "\n".join(
        "<tr>" + "".join(_cell(row[k]) for k in ("name", "origin", "duties", "formalism")) + "</tr>"
        for row in packs
    )
    engine_html = "\n".join(
        "<tr>" + "".join(_cell(row[k]) for k in ("name", "origin", "ceiling", "verified")) + "</tr>"
        for row in engines
    )
    return f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>Reasonsmith registry</title>
<style>body{{margin:0;background:#f5f1e8;color:#20252b;font:16px/1.5 system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:3rem 1.5rem}}header{{background:#17232d;color:#f5f1e8;padding:2rem;border-radius:12px}}h1{{margin:0 0 .4rem;font-size:2.4rem}}h2{{margin-top:2.5rem}}.notice{{border-left:4px solid #c47c28;background:#fff9ed;padding:1rem 1.25rem}}table{{width:100%;border-collapse:collapse;background:#fff;margin:1rem 0 2rem}}th,td{{padding:.7rem .8rem;text-align:left;border-bottom:1px solid #ddd}}th{{background:#e8e1d4}}code{{font-size:.9em}}footer{{color:#58636c;font-size:.9rem}}</style></head>
<body><main><header><h1>Discovery registry</h1><p>Pack and engine inventory exposed by the local Python environment.</p></header>
<p class=\"notice\">{html.escape(DISCLAIMER)}</p>
<h2>Engines</h2><table><thead><tr><th>Name</th><th>Origin</th><th>Declared max strength</th><th>verify-engine</th></tr></thead><tbody>{engine_html}</tbody></table>
<h2>Packs</h2><table><thead><tr><th>Name</th><th>Origin</th><th>Duties</th><th>Formalism split</th></tr></thead><tbody>{pack_html}</tbody></table>
<footer>Generated by <code>{BUILD_COMMAND}</code>. Re-run the builder after changing the installed environment.</footer></main></body></html>
"""


if __name__ == "__main__":
    REGISTRY_HTML.write_text(build(), encoding="utf-8")
