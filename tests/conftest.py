"""Shared fixtures for zkm-photo tests.

zkm_photo is installed editable via `uv sync --extra dev`; tests import
`zkm_photo.convert` directly. The repo-root `convert.py` is only the
filesystem-discovery shim for zkm core and is not imported by tests.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def store(tmp_path: Path) -> Path:
    """Minimal zkm store skeleton."""
    s = tmp_path / "store"
    (s / "photos").mkdir(parents=True)
    (s / "inbox").mkdir()
    (s / "originals" / "photos").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(s)], check=True)
    return s


@pytest.fixture
def src(tmp_path: Path) -> Path:
    """Clean photo source_dir."""
    d = tmp_path / "photos_src"
    d.mkdir()
    return d


def cfg(src: Path) -> dict:
    return {"source_dir": str(src)}
