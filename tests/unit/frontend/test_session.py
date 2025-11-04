"""Unit tests for session state helpers."""

# Mock streamlit before importing session module
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

sys.modules["streamlit"] = MagicMock()

from frontend.streamlit_app.session import (  # noqa: E402
    ChatMessage,
    SessionState,
    add_message,
    ensure_agent_session,
    get_conversation_history,
    get_session_id,
    init_session_state,
    is_token_expired,
    set_tokens,
    start_new_conversation,
)


@pytest.fixture
def mock_st():
    """Mock Streamlit session_state."""
    with patch("frontend.streamlit_app.session.st") as mock:
        # Create a MagicMock that allows attribute assignment
        session_state_mock = MagicMock()
        session_state_mock.__setitem__ = MagicMock()
        session_state_mock.__getitem__ = MagicMock()
        session_state_mock.__contains__ = MagicMock(return_value=False)
        mock.session_state = session_state_mock
        yield mock


class TestChatMessage:
    """Tests for ChatMessage dataclass."""

    def test_create_message(self):
        """Test creating a chat message."""
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert isinstance(msg.timestamp, datetime)

    def test_to_dict(self):
        """Test converting message to dictionary."""
        msg = ChatMessage(role="assistant", content="Hi there")
        data = msg.to_dict()
        assert data["role"] == "assistant"
        assert data["content"] == "Hi there"
        assert "timestamp" in data


class TestSessionState:
    """Tests for SessionState management."""

    def test_init_session_state(self, mock_st):
        """Test initializing session state."""
        # Configure mock to return False for "state" in session_state check
        mock_st.session_state.__contains__.return_value = False

        init_session_state()

        # Verify state was set
        assert mock_st.session_state.state is not None

    def test_set_tokens(self, mock_st):
        """Test storing OAuth2 tokens."""
        # Setup mock session state
        mock_st.session_state.__contains__.return_value = True
        state_instance = SessionState()
        mock_st.session_state.state = state_instance

        set_tokens(
            access_token="access123",
            id_token="id123",
            refresh_token="refresh123",
            expires_in=3600,
        )

        assert state_instance.access_token == "access123"
        assert state_instance.id_token == "id123"
        assert state_instance.refresh_token == "refresh123"
        assert state_instance.authenticated is True
        assert state_instance.token_expiry is not None

    def test_add_message(self, mock_st):
        """Test adding message to conversation history."""
        mock_st.session_state.__contains__.return_value = True
        state_instance = SessionState()
        mock_st.session_state.state = state_instance

        agent_id = "warranty-docs"
        ensure_agent_session(agent_id)

        add_message(agent_id, "user", "What is the warranty?")

        history = state_instance.agent_sessions[agent_id].conversation_history
        assert len(history) == 1
        assert history[0].role == "user"
        assert history[0].content == "What is the warranty?"

    def test_start_new_conversation(self, mock_st):
        """Test starting a new conversation for a specific agent."""
        mock_st.session_state.__contains__.return_value = True
        state_instance = SessionState()
        mock_st.session_state.state = state_instance

        agent_id = "customer-support"
        ensure_agent_session(agent_id)
        add_message(agent_id, "user", "Old message")

        old_session_id = get_session_id(agent_id)

        start_new_conversation(agent_id)

        new_session = state_instance.agent_sessions[agent_id]
        assert new_session.session_id != old_session_id
        assert len(new_session.conversation_history) == 0

    def test_multi_agent_conversations_isolated(self, mock_st):
        """Ensure separate agents maintain independent histories."""

        mock_st.session_state.__contains__.return_value = True
        state_instance = SessionState()
        mock_st.session_state.state = state_instance

        agent_a = "warranty-docs"
        agent_b = "customer-support"

        ensure_agent_session(agent_a)
        ensure_agent_session(agent_b)

        add_message(agent_a, "user", "Hi warranty")
        add_message(agent_b, "user", "Hi customer support")

        history_a = get_conversation_history(agent_a)
        history_b = get_conversation_history(agent_b)

        assert len(history_a) == 1
        assert len(history_b) == 1
        assert history_a[0].content == "Hi warranty"
        assert history_b[0].content == "Hi customer support"

    def test_is_token_expired_no_expiry(self, mock_st):
        """Test token expiration check with no expiry set."""
        mock_st.session_state.__contains__.return_value = True
        state_instance = SessionState()
        mock_st.session_state.state = state_instance

        assert is_token_expired() is True

    def test_is_token_expired_expired(self, mock_st):
        """Test token expiration check with expired token."""
        mock_st.session_state.__contains__.return_value = True
        state_instance = SessionState()
        state_instance.token_expiry = datetime.utcnow() - timedelta(hours=1)
        mock_st.session_state.state = state_instance

        assert is_token_expired() is True

    def test_is_token_expired_valid(self, mock_st):
        """Test token expiration check with valid token."""
        mock_st.session_state.__contains__.return_value = True
        state_instance = SessionState()
        state_instance.token_expiry = datetime.utcnow() + timedelta(hours=1)
        mock_st.session_state.state = state_instance

        assert is_token_expired() is False

    def test_is_token_expired_soon(self, mock_st):
        """Test token expiration check with token expiring soon."""
        mock_st.session_state.__contains__.return_value = True
        state_instance = SessionState()
        # Token expires in 3 minutes (within 5-minute buffer)
        state_instance.token_expiry = datetime.utcnow() + timedelta(minutes=3)
        mock_st.session_state.state = state_instance

        assert is_token_expired() is True
