"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

import pytest

# Add packages to Python path immediately (before test collection)
root = Path(__file__).parent.parent
packages_root = root / "packages"

for package_dir in packages_root.iterdir():
    if package_dir.is_dir() and (package_dir / "src").exists():
        sys.path.insert(0, str(package_dir / "src"))


@pytest.fixture
def mock_aws_credentials(monkeypatch):
    """Mock AWS credentials for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
