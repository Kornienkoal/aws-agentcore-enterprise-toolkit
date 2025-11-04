"""Unit tests for MemoryHooks (AgentCore Memory integration)."""

from types import SimpleNamespace
from unittest.mock import MagicMock


def _make_msg(role: str, texts: list[str]):
    return SimpleNamespace(
        message={
            "role": role,
            "content": [{"type": "output_text", "text": t} for t in texts],
        }
    )


class TestMemoryHooks:
    def setup_method(self):
        from agentcore_tools.memory import MemoryHooks

        self.client = MagicMock()
        self.logger = MagicMock()
        self.hooks = MemoryHooks(
            memory_client=self.client,
            memory_id="mem-123",
            actor_id="user-abc",
            session_id="sess-xyz",
            logger=self.logger,
        )

    def test_persists_messages_on_after_invocation(self):
        # Given two conversation messages
        self.hooks._on_message(_make_msg("user", ["Hello there"]))
        self.hooks._on_message(_make_msg("assistant", ["Hi! How can I help?", "More text"]))

        # When invocation completes
        self.hooks._on_after_invocation(SimpleNamespace())

        # Then a single memory event is written with both messages
        self.client.create_event.assert_called_once()
        kwargs = self.client.create_event.call_args.kwargs
        assert kwargs["memory_id"] == "mem-123"
        assert kwargs["actor_id"] == "user-abc"
        assert kwargs["session_id"] == "sess-xyz"
        # Messages should contain aggregated text and proper roles
        assert kwargs["messages"] == [
            ("Hello there", "USER"),
            ("Hi! How can I help?\nMore text", "ASSISTANT"),
        ]
        # Buffer cleared
        assert self.hooks._messages == []

    def test_no_messages_is_noop(self):
        # When no messages were collected, nothing is written
        self.hooks._on_after_invocation(SimpleNamespace())
        self.client.create_event.assert_not_called()

    def test_client_error_is_non_fatal_and_clears_buffer(self):
        # Given a collected message
        self.hooks._on_message(_make_msg("user", ["Hi"]))
        # And the client fails
        self.client.create_event.side_effect = RuntimeError("boom")

        # When after invocation fires
        self.hooks._on_after_invocation(SimpleNamespace())

        # Then failure is logged but does not raise
        self.logger.warning.assert_called()
        # Buffer cleared regardless
        assert self.hooks._messages == []
