"""Older name for validate.py, kept so existing instructions keep working.

    python check_deck.py deck.pptx [--spec deck.json]

Runs every check in validate.py. Prefer make_deck.py, which builds and validates in one step.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate  # noqa: E402

if __name__ == "__main__":
    validate.main()
