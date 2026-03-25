"""Shim: `python main.py` delegates to the package CLI (after `pip install -e .`)."""

import sys
from pathlib import Path

# Allow running without editable install during development
_src = Path(__file__).resolve().parent / "src"
if _src.is_dir():
    sys.path.insert(0, str(_src))

from medicineai.cli import main

if __name__ == "__main__":
    main()
