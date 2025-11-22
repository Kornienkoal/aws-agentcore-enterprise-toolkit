"""Streamlit UI components for the AgentCore demo application."""

from __future__ import annotations

import streamlit as st

from .session import (
    get_conversation_history,
    get_session_state,
    start_new_conversation,
)


def render_header() -> None:
    """Render the application header with title and navigation."""
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        st.title("🤖 Customer Support Agent")

    state = get_session_state()

    with col2:
        if state.authenticated and st.button("🆕 New Conversation"):
            current_agent = st.session_state.get("selected_agent")
            if current_agent:
                start_new_conversation(current_agent)
            st.rerun()

    with col3:
        if state.authenticated and st.button("🚪 Logout"):
            # Set logout flag for main.py to handle
            st.session_state.should_logout = True
            st.rerun()


def render_auth_status() -> None:
    """Render authentication status information."""
    state = get_session_state()

    if state.authenticated:
        email = state.email or state.username or state.user_id
        st.success(f"✅ Logged in as: **{email}**")
    else:
        st.info("👤 Please log in to start chatting with the agent.")


def render_login_button(login_url: str | None = None) -> None:
    """Render the login button for unauthenticated users.

    Args:
        login_url: Pre-generated Cognito authorization URL (if available)
    """
    st.markdown("### Welcome to Customer Support")
    st.markdown(
        "This demo connects you with an AI-powered customer support agent "
        "that can help answer questions about warranties, products, and policies."
    )

    if login_url:
        # Show direct link to Cognito (use target="_top" to break out of iframe)
        st.markdown(
            f'<a href="{login_url}" target="_top" style="display: inline-block; padding: 0.5rem 1rem; background-color: #ff4b4b; color: white; text-decoration: none; border-radius: 0.25rem; font-weight: 600;">🔐 Login with Cognito</a>',
            unsafe_allow_html=True,
        )
    else:
        if st.button("🔐 Login with Cognito", type="primary"):
            # Set login flag for main.py to handle redirect
            st.session_state.should_login = True
            st.rerun()


def render_chat_interface() -> None:
    """Render the chat interface for authenticated users."""
    agent_id = st.session_state.get("selected_agent")
    if not agent_id:
        st.info("Select an agent to begin chatting.")
        return

    # Display conversation history for the active agent
    for message in get_conversation_history(agent_id):
        with st.chat_message(message.role):
            st.markdown(message.content)
            if message.role == "assistant":
                st.caption(f"🕐 {message.timestamp.strftime('%H:%M:%S')}")

    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Set message flag for main.py to handle agent invocation
        st.session_state.pending_message = {
            "agent_id": agent_id,
            "prompt": prompt,
        }
        st.rerun()


def render_error(error_message: str) -> None:
    """Render an error message.

    Args:
        error_message: Error message to display
    """
    st.error(f"❌ {error_message}")


def render_loading(message: str = "Processing...") -> None:
    """Render a loading indicator.

    Args:
        message: Loading message to display
    """
    with st.spinner(message):
        pass


def render_info(message: str) -> None:
    """Render an informational message.

    Args:
        message: Info message to display
    """
    st.info(f"ℹ️ {message}")
