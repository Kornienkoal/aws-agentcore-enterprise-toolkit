"""Session state helpers for Streamlit app."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import streamlit as st


@dataclass
class ChatMessage:
    """Represents a single message in a conversation."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SessionState:
    """Typed wrapper around Streamlit's session state."""

    # Authentication
    authenticated: bool = False
    access_token: str | None = None
    id_token: str | None = None
    refresh_token: str | None = None
    token_expiry: datetime | None = None

    # User identity
    user_id: str | None = None
    email: str | None = None
    username: str | None = None

    # Conversation
    # Conversations keyed by agent identifier
    agent_sessions: dict[str, AgentSession] = field(default_factory=dict)


@dataclass
class AgentSession:
    """Conversation context for a specific agent."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    conversation_history: list[ChatMessage] = field(default_factory=list)


def init_session_state() -> None:
    """Initialize Streamlit session state with default values.

    Call this at the start of the app to ensure all required state exists.
    """
    if "state" not in st.session_state:
        st.session_state.state = SessionState()


def get_session_state() -> SessionState:
    """Get the current session state.

    Returns:
        SessionState instance from Streamlit's session state

    Raises:
        RuntimeError: If session state not initialized
    """
    if "state" not in st.session_state:
        raise RuntimeError("Session state not initialized. Call init_session_state() first.")
    return st.session_state.state


def reset_session_state() -> None:
    """Reset session state to initial values (logout)."""
    st.session_state.state = SessionState()


def get_agent_session(agent_id: str) -> AgentSession:
    """Ensure and return the conversation context for a given agent."""

    state = get_session_state()
    if agent_id not in state.agent_sessions:
        state.agent_sessions[agent_id] = AgentSession()
    return state.agent_sessions[agent_id]


def ensure_agent_session(agent_id: str) -> None:
    """Guarantee that an agent session exists (no-op if already present)."""

    get_agent_session(agent_id)


def start_new_conversation(agent_id: str) -> None:
    """Start a fresh conversation for the specified agent."""

    session = get_agent_session(agent_id)
    session.session_id = str(uuid.uuid4())
    session.conversation_history.clear()


def set_tokens(
    access_token: str,
    id_token: str,
    refresh_token: str,
    expires_in: int,
) -> None:
    """Store OAuth2 tokens in session state.

    Args:
        access_token: OAuth2 access token
        id_token: JWT with user claims
        refresh_token: Token for renewal
        expires_in: Token validity duration in seconds
    """
    state = get_session_state()
    state.access_token = access_token
    state.id_token = id_token
    state.refresh_token = refresh_token
    state.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
    state.authenticated = True


def add_message(agent_id: str, role: str, content: str) -> None:
    """Append a chat message to the specified agent's conversation history."""
    session = get_agent_session(agent_id)
    message = ChatMessage(role=role, content=content)
    session.conversation_history.append(message)


def get_conversation_history(agent_id: str) -> list[ChatMessage]:
    """Return the conversation history for an agent."""

    return get_agent_session(agent_id).conversation_history


def get_session_id(agent_id: str) -> str:
    """Return the Bedrock runtime session identifier for an agent."""

    return get_agent_session(agent_id).session_id


def is_token_expired() -> bool:
    """Check if the access token is expired or will expire soon.

    Returns:
        True if token is expired or expires within 5 minutes
    """
    state = get_session_state()
    if not state.token_expiry:
        return True
    # Consider token expired if less than 5 minutes remaining
    return datetime.utcnow() >= state.token_expiry - timedelta(minutes=5)
