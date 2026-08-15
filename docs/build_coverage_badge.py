"""Build the repository-hosted coverage badge from coverage.py JSON output."""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path


def build_badge(source: Path, destination: Path) -> None:
    """Render a deterministic SVG badge whose value comes from a coverage JSON report."""
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
        percent = float(data["totals"]["percent_covered"])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ValueError(f"coverage JSON has no usable totals.percent_covered: {exc}") from exc
    if not 0 <= percent <= 100:
        raise ValueError("coverage percentage must be between 0 and 100")
    value = f"{percent:.1f}%"
    color = "#2da44e" if percent >= 95.0 else "#cf222e"
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="128" height="20" role="img" '
        f'aria-label="coverage: {escape(value)}"><title>coverage: {escape(value)}</title>'
        '<rect width="128" height="20" rx="3" fill="#555"/>'
        '<rect x="67" width="61" height="20" rx="3" fill="' + color + '"/>'
        '<text x="33.5" y="14" fill="#fff" text-anchor="middle" '
        'font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">coverage</text>'
        f'<text x="97.5" y="14" fill="#fff" text-anchor="middle" '
        f'font-family="Verdana,Geneva,DejaVu Sans,sans-serif" font-size="11">{escape(value)}</text>'
        '</svg>\n'
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(svg, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    build_badge(args.source, args.destination)


if __name__ == "__main__":
    main()
