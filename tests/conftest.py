"""Shared test fixtures for SearchPaper."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("SEARCHPAPER_CACHE", str(Path(tempfile.gettempdir()) / "searchpaper-tests" / "cache.db"))

from searchpaper.cache import Cache


@pytest.fixture
def tmp_cache(tmp_path):
    return Cache(str(tmp_path / "cache.db"))
