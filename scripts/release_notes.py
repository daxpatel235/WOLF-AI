"""
Prints the CHANGELOG.md section for a version, or writes it to a file:
    python scripts/release_notes.py 2.0.0
    python scripts/release_notes.py 2.0.0 release-notes.md
"""
import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parents[1] / "CHANGELOG.md"


def section(version):
    text = CHANGELOG.read_text(encoding="utf-8")
    match = re.search(rf"^## \[?{re.escape(version)}\]?.*?$\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not match:
        raise SystemExit(f"CHANGELOG.md has no section for {version}")
    return match.group(1).strip()


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: release_notes.py <version> [output-file]")
    notes = section(sys.argv[1])
    if len(sys.argv) == 3:
        Path(sys.argv[2]).write_text(notes + "\n", encoding="utf-8")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(notes)
