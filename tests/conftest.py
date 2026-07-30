import sys
from pathlib import Path

# src layout, and deliberately no editable install: this repo is worked on in disposable worktrees,
# and an editable install would leave the environment pointing at a checkout that later vanishes.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
