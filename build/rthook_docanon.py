"""Runtime hook: paths for frozen DocAnon (PyInstaller)."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _setup() -> None:
    if not getattr(sys, "frozen", False):
        return
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return
    root = Path(meipass)

    # spaCy model path hint
    model = root / "ru_core_news_lg"
    if model.is_dir():
        os.environ.setdefault("DOCANON_SPACY_MODEL", str(model))

    # ensure package imports from bundle
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_setup()
