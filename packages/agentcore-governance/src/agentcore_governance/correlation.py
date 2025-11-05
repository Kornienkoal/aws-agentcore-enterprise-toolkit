"""Correlation ID helpers aligning audit events across systems."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass


@dataclass(frozen=True)
class CorrelationContext:
    trace_id: str
    user: str | None = None
    agent: str | None = None
    tool: str | None = None

    def to_headers(self) -> Mapping[str, str]:
        """Render correlation metadata as outbound headers."""
        parts: list[str] = [f"trace={self.trace_id}"]
        if self.user:
            parts.append(f"user={self.user}")
        if self.agent:
            parts.append(f"agent={self.agent}")
        if self.tool:
            parts.append(f"tool={self.tool}")
        return {"X-Correlation-Id": ";".join(parts)}


@contextmanager
def new_correlation_context(
    *, user: str | None = None, agent: str | None = None, tool: str | None = None
):
    """Create a new correlation context with a generated trace identifier.

    Usage:
        with new_correlation_context() as corr_id:
            # Use corr_id for logging/tracing
            pass

    Yields:
        Correlation trace_id (str)
    """
    trace_id = uuid.uuid4().hex
    ctx = CorrelationContext(trace_id=trace_id, user=user, agent=agent, tool=tool)
    yield ctx.trace_id
