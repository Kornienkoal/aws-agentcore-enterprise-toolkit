"""Functional tests for Phase 2 (US2): Tool Access Governance.

Tests the complete authorization workflow end-to-end using real implementations.
"""

from __future__ import annotations

from agentcore_governance import authorization, classification
from agentcore_governance.api import authorization_handlers


class TestPhase2AuthorizationWorkflow:
    """End-to-end tests for authorization and tool governance features."""

    def setup_method(self) -> None:
        """Clear authorization store before each test."""
        authorization.clear_authorization_store()

    def test_agent_tool_mapping_crud(self) -> None:
        """Create, read, update authorization mappings."""
        agent_id = "customer-support-agent"

        # Initially empty
        tools = authorization.get_authorized_tools(agent_id)
        assert tools == []

        # Set initial tools
        report = authorization.set_authorized_tools(
            agent_id=agent_id,
            tools=["get_product_info", "search_documentation"],
            reason="Initial authorization for customer support",
        )

        assert report["agent_id"] == agent_id
        assert set(report["added"]) == {"get_product_info", "search_documentation"}
        assert report["removed"] == []
        assert report["unchanged"] == []

        # Verify retrieval
        tools = authorization.get_authorized_tools(agent_id)
        assert set(tools) == {"get_product_info", "search_documentation"}

        # Add more tools
        report = authorization.set_authorized_tools(
            agent_id=agent_id,
            tools=["get_product_info", "search_documentation", "check_warranty"],
            reason="Adding warranty check capability",
        )

        assert report["added"] == ["check_warranty"]
        assert set(report["unchanged"]) == {"get_product_info", "search_documentation"}
        assert report["removed"] == []

        # Remove a tool
        report = authorization.set_authorized_tools(
            agent_id=agent_id,
            tools=["get_product_info", "check_warranty"],
            reason="Removing documentation search",
        )

        assert report["removed"] == ["search_documentation"]
        assert set(report["unchanged"]) == {"get_product_info", "check_warranty"}
        assert report["added"] == []

    def test_classification_enforcement(self, tool_registry: dict) -> None:
        """Test classification-based authorization enforcement."""
        registry = tool_registry

        # LOW classification: auto-approved
        authorized, reason = classification.validate_tool_authorization(
            tool_id="get_product_info",
            approval_record=None,
            registry=registry,
        )
        assert authorized is True
        assert "LOW" in reason

        # MODERATE classification: auto-approved
        authorized, reason = classification.validate_tool_authorization(
            tool_id="check_warranty",
            approval_record=None,
            registry=registry,
        )
        assert authorized is True
        assert "MODERATE" in reason

        # SENSITIVE classification without approval: denied
        authorized, reason = classification.validate_tool_authorization(
            tool_id="update_customer_record",
            approval_record=None,
            registry=registry,
        )
        assert authorized is False
        assert "SENSITIVE" in reason
        assert "approval" in reason.lower()

        # SENSITIVE classification with approval: authorized
        approval = {
            "approved_by": "security-team@example.com",
            "approved_at": "2025-11-01T10:00:00Z",
            "justification": "Required for customer service workflow",
        }
        authorized, reason = classification.validate_tool_authorization(
            tool_id="update_customer_record",
            approval_record=approval,
            registry=registry,
        )
        assert authorized is True
        assert "approved" in reason.lower()

    def test_authorization_endpoints_workflow(self, tool_registry: dict) -> None:
        """Test GET/PUT authorization endpoints."""
        agent_id = "warranty-docs-agent"

        # GET empty authorization list
        response = authorization_handlers.get_agent_tools(agent_id)
        assert response["agent_id"] == agent_id
        assert response["authorized_tools"] == []
        assert response["total_count"] == 0

        # PUT initial authorization (LOW tools only)
        response = authorization_handlers.update_agent_tools(
            agent_id=agent_id,
            tools=["get_product_info", "search_documentation"],
            reason="Initial setup for warranty agent",
            validate_classification=True,
            classification_registry=tool_registry,
            approval_records=None,
        )

        assert response["success"] is True
        assert set(response["authorized_tools"]) == {"get_product_info", "search_documentation"}
        assert set(response["changes"]["added"]) == {"get_product_info", "search_documentation"}
        assert len(response["audit_events"]) == 2  # One event per tool added

        # GET updated authorization list
        response = authorization_handlers.get_agent_tools(agent_id)
        assert response["total_count"] == 2
        assert set(response["authorized_tools"]) == {"get_product_info", "search_documentation"}

        # PUT with MODERATE tool
        response = authorization_handlers.update_agent_tools(
            agent_id=agent_id,
            tools=["get_product_info", "search_documentation", "web_search"],
            reason="Adding web search capability",
            validate_classification=True,
            classification_registry=tool_registry,
            approval_records=None,
        )

        assert response["success"] is True
        assert "web_search" in response["authorized_tools"]
        assert response["changes"]["added"] == ["web_search"]

    def test_sensitive_tool_rejection_without_approval(self, tool_registry: dict) -> None:
        """Test that SENSITIVE tools are rejected without approval records."""
        agent_id = "test-agent"

        # Try to add SENSITIVE tool without approval
        response = authorization_handlers.update_agent_tools(
            agent_id=agent_id,
            tools=["get_product_info", "update_customer_record"],  # SENSITIVE
            reason="Adding customer record updates",
            validate_classification=True,
            classification_registry=tool_registry,
            approval_records=None,
        )

        assert response["success"] is False
        assert "update_customer_record" in response["error"]
        assert "SENSITIVE" in response["error"]
        assert "approval" in response["error"].lower()

    def test_sensitive_tool_approval_workflow(self, tool_registry: dict) -> None:
        """Test SENSITIVE tool authorization with approval records."""
        agent_id = "privileged-agent"

        approval_records = {
            "update_customer_record": {
                "approved_by": "security-lead@example.com",
                "approved_at": "2025-11-05T08:00:00Z",
                "justification": "Required for tier-2 support escalations",
            }
        }

        # Add SENSITIVE tool with approval
        response = authorization_handlers.update_agent_tools(
            agent_id=agent_id,
            tools=["get_product_info", "update_customer_record"],
            reason="Tier-2 agent with customer record access",
            validate_classification=True,
            classification_registry=tool_registry,
            approval_records=approval_records,
        )

        assert response["success"] is True
        assert "update_customer_record" in response["authorized_tools"]
        assert len(response["audit_events"]) == 2

        # Verify audit event for SENSITIVE tool
        sensitive_event = next(
            e for e in response["audit_events"] if e["tool_id"] == "update_customer_record"
        )
        assert sensitive_event["effect"] == "allow"
        assert "classification" in sensitive_event

    def test_authorization_decision_and_audit(self, tool_registry: dict) -> None:
        """Test authorization decision checks with audit trail."""
        agent_id = "audit-test-agent"
        correlation_id = "test-correlation-123"

        # Set up authorization
        authorization.set_authorized_tools(
            agent_id=agent_id,
            tools=["get_product_info", "check_warranty"],
            reason="Test setup",
        )

        # Check authorized tool
        response = authorization_handlers.check_tool_access(
            agent_id=agent_id,
            tool_id="get_product_info",
            correlation_id=correlation_id,
            classification_registry=tool_registry,
        )

        assert response["agent_id"] == agent_id
        assert response["tool_id"] == "get_product_info"
        assert response["effect"] == "allow"
        assert response["authorized"] is True
        assert "audit_event" in response
        assert response["audit_event"]["event_type"] == "authorization_decision"
        assert response["audit_event"]["correlation_id"] == correlation_id

        # Check unauthorized tool
        response = authorization_handlers.check_tool_access(
            agent_id=agent_id,
            tool_id="web_search",
            correlation_id=correlation_id,
            classification_registry=tool_registry,
        )

        assert response["effect"] == "deny"
        assert response["authorized"] is False
        assert "NOT in authorized list" in response["reason"]
        assert response["audit_event"]["effect"] == "deny"

    def test_differential_change_tracking(self) -> None:
        """Test differential reporting of authorization changes."""
        agent_id = "tracked-agent"

        # Initial authorization
        report1 = authorization.set_authorized_tools(
            agent_id=agent_id,
            tools=["tool1", "tool2", "tool3"],
            reason="Initial setup",
        )
        assert set(report1["added"]) == {"tool1", "tool2", "tool3"}

        # Modify: remove tool2, add tool4, keep tool1 and tool3
        report2 = authorization.set_authorized_tools(
            agent_id=agent_id,
            tools=["tool1", "tool3", "tool4"],
            reason="Swap tool2 for tool4",
        )
        assert report2["added"] == ["tool4"]
        assert report2["removed"] == ["tool2"]
        assert set(report2["unchanged"]) == {"tool1", "tool3"}

        # Get full history
        history = authorization.generate_differential_report(agent_id)
        assert len(history) == 2
        assert history[0]["reason"] == "Initial setup"
        assert history[1]["reason"] == "Swap tool2 for tool4"


class TestPhase2AcceptanceCriteria:
    """Verify independent acceptance criteria for Phase 2 (US2)."""

    def setup_method(self) -> None:
        """Clear authorization store before each test."""
        authorization.clear_authorization_store()

    def test_independent_criterion_tool_removal_denial(self, tool_registry: dict) -> None:
        """Independent criterion: Remove tool via PUT → subsequent invocation denied."""
        agent_id = "criterion-test-agent"
        correlation_id = "criterion-test-correlation"

        # Step 1: Authorize tools
        authorization.set_authorized_tools(
            agent_id=agent_id,
            tools=["get_product_info", "check_warranty", "web_search"],
            reason="Initial authorization",
        )

        # Step 2: Verify tool is authorized
        check1 = authorization_handlers.check_tool_access(
            agent_id=agent_id,
            tool_id="check_warranty",
            correlation_id=correlation_id,
            classification_registry=tool_registry,
        )
        assert check1["effect"] == "allow"
        assert check1["authorized"] is True

        # Step 3: Remove tool via PUT endpoint
        update_response = authorization_handlers.update_agent_tools(
            agent_id=agent_id,
            tools=["get_product_info", "web_search"],  # Removed check_warranty
            reason="Removing warranty check capability",
            validate_classification=False,
            classification_registry=tool_registry,
            approval_records=None,
        )
        assert update_response["success"] is True
        assert "check_warranty" in update_response["changes"]["removed"]

        # Step 4: Verify tool is now denied
        check2 = authorization_handlers.check_tool_access(
            agent_id=agent_id,
            tool_id="check_warranty",
            correlation_id=correlation_id,
            classification_registry=tool_registry,
        )
        assert check2["effect"] == "deny"
        assert check2["authorized"] is False
        assert "NOT in authorized list" in check2["reason"]

        # Step 5: Verify audit trail
        assert check2["audit_event"]["effect"] == "deny"
        assert check2["audit_event"]["tool_id"] == "check_warranty"
