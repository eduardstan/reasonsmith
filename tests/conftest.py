import sys
from pathlib import Path

# src layout: `src` goes on the path so this package itself needs no install to be imported by the
# tests. nesyarena still does — see the README, "Install and run", for the one install path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
