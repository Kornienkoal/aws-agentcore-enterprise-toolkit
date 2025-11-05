"""Functional test fixtures and configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to functional test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_principals(fixtures_dir: Path) -> list[dict]:
    """Load sample principals from YAML fixture."""
    fixture_file = fixtures_dir / "sample_principals.yaml"
    with fixture_file.open() as f:
        data = yaml.safe_load(f)
    return data["principals"]


@pytest.fixture
def tool_registry(fixtures_dir: Path) -> dict:
    """Load tool classification registry from YAML fixture."""
    fixture_file = fixtures_dir / "tool_registry.yaml"
    with fixture_file.open() as f:
        return yaml.safe_load(f)
