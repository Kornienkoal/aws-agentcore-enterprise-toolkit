"""E2E test fixtures: ensure Streamlit app is running for Playwright tests.

This fixture starts the Streamlit app on localhost:8501 before E2E tests
and shuts it down afterwards. It uses uv to run the app with the workspace
environment so local packages are available.
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Generator

import pytest
import requests


def _is_up(url: str) -> bool:
    try:
        r = requests.get(url, timeout=1.0)
        return r.status_code < 500
    except Exception:
        return False


@pytest.fixture(scope="session", autouse=True)
def ensure_streamlit_running() -> Generator[None]:
    """Start Streamlit server for E2E tests and stop after session.

    Set E2E_START_SERVER=0 to disable auto-start (use external server).
    """
    if os.getenv("E2E_START_SERVER", "1") != "1":
        # Assume external server is running
        yield
        return

    env = os.environ.copy()
    env.setdefault("AGENTCORE_ENV", "dev")
    env.setdefault("AWS_REGION", "us-east-1")
    # Headless mode; fixed port for tests
    cmd = [
        "uv",
        "run",
        "streamlit",
        "run",
        "frontend/streamlit_app/main.py",
        "--server.port",
        "8501",
        "--server.headless",
        "true",
    ]

    # Start server in project root
    proc = subprocess.Popen(
        cmd,
        cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for health endpoint or root to respond
    base = "http://localhost:8501"
    health_urls = [f"{base}/_stcore/health", base]

    start = time.time()
    timeout_s = 60
    ready = False
    while time.time() - start < timeout_s:
        if any(_is_up(u) for u in health_urls):
            ready = True
            break
        # If process exited early, fail fast
        if proc.poll() is not None:
            break
        time.sleep(0.5)

    if not ready:
        # Include some stderr context for troubleshooting
        try:
            _, stderr = proc.communicate(timeout=2)
        except Exception:
            stderr = ""
        proc.terminate()
        raise RuntimeError(f"Streamlit app did not start within {timeout_s}s. Stderr:\n{stderr}")

    # Yield to tests
    try:
        yield
    finally:
        # Gracefully terminate
        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        # Drain remaining output to avoid zombies
        import contextlib

        with contextlib.suppress(Exception):
            proc.communicate(timeout=2)
