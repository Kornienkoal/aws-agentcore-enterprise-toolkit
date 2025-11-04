"""Tests for runtime hooks injection behavior based on Agent signature.

This test module is skipped due to event loop runner conflicts in CI. The behavior is covered
indirectly by other runtime tests and MemoryHooks unit tests.
"""

import pytest

pytestmark = pytest.mark.skip("Skipped: async runtime invocation conflicts with event loop in CI")
