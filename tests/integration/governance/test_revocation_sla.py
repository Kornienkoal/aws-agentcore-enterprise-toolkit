"""Tests for revocation SLA compliance and synthetic monitoring."""

from __future__ import annotations

import time

import pytest
from agentcore_governance import revocation, revocation_synthetic
from agentcore_governance.api import revocation_handlers


@pytest.fixture(autouse=True)
def reset_revocation_registry():
    """Reset revocation registry before each test."""
    revocation._revocations_registry.clear()
    yield
    revocation._revocations_registry.clear()


class TestRevocationSLACompliance:
    """Test revocation SLA behavior and metrics."""

    def test_fast_revocation_meets_sla(self):
        """Test that a fast revocation meets SLA."""
        # Create revocation
        revocation_id = revocation.create_revocation_request(
            {
                "subjectType": "user",
                "subjectId": "user-123",
                "scope": "user_access",
            }
        )

        # Immediately propagate (simulate fast system)
        revocation.mark_revocation_propagated(revocation_id)

        # Check SLA status
        revocation_record = revocation.get_revocation_status(revocation_id)
        assert revocation_record["sla_met"] is True

    def test_slow_revocation_breaches_sla(self):
        """Test that a slow revocation breaches SLA."""
        # Override SLA target to 0 seconds for testing
        original_sla = revocation.DEFAULT_SLA_TARGET_SECONDS
        revocation.DEFAULT_SLA_TARGET_SECONDS = 0

        try:
            # Create revocation
            revocation_id = revocation.create_revocation_request(
                {
                    "subjectType": "user",
                    "subjectId": "user-123",
                    "scope": "user_access",
                }
            )

            # Wait a bit to ensure SLA breach
            time.sleep(0.01)

            # Propagate
            revocation.mark_revocation_propagated(revocation_id)

            # Check SLA status
            revocation_record = revocation.get_revocation_status(revocation_id)
            assert revocation_record["sla_met"] is False

        finally:
            revocation.DEFAULT_SLA_TARGET_SECONDS = original_sla

    def test_sla_metrics_aggregate_correctly(self):
        """Test that SLA metrics aggregate multiple revocations."""
        # Override SLA target for controlled testing
        original_sla = revocation.DEFAULT_SLA_TARGET_SECONDS
        revocation.DEFAULT_SLA_TARGET_SECONDS = 0.1

        try:
            # Create mix of fast and slow revocations
            id1 = revocation.create_revocation_request(
                {
                    "subjectType": "user",
                    "subjectId": "user-fast",
                    "scope": "user_access",
                }
            )
            revocation.mark_revocation_propagated(id1)  # Fast = meets SLA

            id2 = revocation.create_revocation_request(
                {
                    "subjectType": "user",
                    "subjectId": "user-slow",
                    "scope": "user_access",
                }
            )
            time.sleep(0.15)  # Exceed SLA
            revocation.mark_revocation_propagated(id2)  # Slow = breaches SLA

            # Get metrics
            metrics = revocation.compute_sla_metrics()

            assert metrics["total_revocations"] == 2
            assert metrics["sla_met_count"] >= 1
            assert metrics["sla_breached_count"] >= 1
            assert 0 <= metrics["sla_compliance_rate"] <= 100

        finally:
            revocation.DEFAULT_SLA_TARGET_SECONDS = original_sla

    def test_pending_revocations_excluded_from_sla_metrics(self):
        """Test that pending revocations don't affect SLA metrics."""
        # Create pending revocation
        revocation.create_revocation_request(
            {
                "subjectType": "user",
                "subjectId": "user-pending",
                "scope": "user_access",
            }
        )

        # Get metrics
        metrics = revocation.compute_sla_metrics()

        # Should not count pending in SLA calculations
        assert metrics["total_revocations"] == 0

    def test_sla_metric_emission_structure(self):
        """Test that emitted SLA metrics have correct structure."""
        # Create and complete a revocation
        revocation_id = revocation.create_revocation_request(
            {
                "subjectType": "user",
                "subjectId": "user-123",
                "scope": "user_access",
            }
        )
        revocation.mark_revocation_propagated(revocation_id)

        # Emit metric
        metric = revocation.emit_sla_metric()

        # Verify structure
        assert metric["metric_name"] == "RevocationSLACompliance"
        assert metric["namespace"] == "AgentCoreGovernance"
        assert "dimensions" in metric
        assert "value" in metric
        assert 0 <= metric["value"] <= 100


class TestSyntheticRevocationTests:
    """Test synthetic revocation testing framework."""

    def test_single_synthetic_test_runs_successfully(self):
        """Test that a single synthetic test executes the full lifecycle."""
        synthetic = revocation_synthetic.SyntheticRevocationTest()

        result = synthetic.run_revocation_test(
            subject_type="user",
            subject_id="synthetic-user-1",
            scope="user_access",
        )

        # Verify test completed
        assert result["test_passed"] is True
        assert result["revocation_id"] is not None
        assert result["access_blocked"] is True
        assert result["latency_ms"] > 0
        assert result["sla_met"] is True

    def test_synthetic_test_with_slow_propagation(self):
        """Test synthetic test detects SLA breach."""
        # Override SLA target for testing
        original_sla = revocation.DEFAULT_SLA_TARGET_SECONDS
        revocation.DEFAULT_SLA_TARGET_SECONDS = 0.001  # 1ms (very tight)

        try:
            synthetic = revocation_synthetic.SyntheticRevocationTest()

            # Add delay before propagation
            def slow_propagate(rev_id):
                time.sleep(0.01)  # 10ms delay
                return revocation_handlers.handle_revocation_propagate(rev_id)

            # Monkey-patch for this test
            original_propagate = revocation_handlers.handle_revocation_propagate
            revocation_handlers.handle_revocation_propagate = slow_propagate

            result = synthetic.run_revocation_test(
                subject_type="user",
                subject_id="synthetic-slow",
                scope="user_access",
            )

            # Should detect SLA breach
            assert result["sla_met"] is False

            # Restore
            revocation_handlers.handle_revocation_propagate = original_propagate

        finally:
            revocation.DEFAULT_SLA_TARGET_SECONDS = original_sla

    def test_multiple_synthetic_tests_aggregate_metrics(self):
        """Test that multiple synthetic tests produce summary metrics."""
        synthetic = revocation_synthetic.SyntheticRevocationTest()

        summary = synthetic.run_multiple_tests(count=5)

        # Verify summary structure
        assert summary["total_tests"] == 5
        assert summary["passed"] <= 5
        assert summary["failed"] >= 0
        assert summary["avg_latency_ms"] > 0
        assert 0 <= summary["sla_compliance_rate"] <= 100
        assert len(summary["individual_results"]) == 5

    def test_synthetic_test_verifies_access_blocked(self):
        """Test that synthetic test confirms access is blocked."""
        synthetic = revocation_synthetic.SyntheticRevocationTest()

        result = synthetic.run_revocation_test(
            subject_type="integration",
            subject_id="synthetic-integration",
            scope="integration_access",
        )

        # Verify access check was performed
        assert result["access_blocked"] is True

        # Verify revocation is actually present
        is_revoked = revocation.is_subject_revoked("integration", "synthetic-integration")
        assert is_revoked is True

    def test_synthetic_test_with_all_subject_types(self):
        """Test synthetic tests work for all subject types."""
        synthetic = revocation_synthetic.SyntheticRevocationTest()

        subject_types = ["user", "integration", "tool", "agent", "principal"]

        for subject_type in subject_types:
            result = synthetic.run_revocation_test(
                subject_type=subject_type,
                subject_id=f"synthetic-{subject_type}",
                scope="user_access",  # Using same scope for simplicity
            )

            assert result["test_passed"] is True
            assert result["access_blocked"] is True


class TestRevocationLatencyTracking:
    """Test accurate latency tracking for revocations."""

    def test_latency_recorded_in_milliseconds(self):
        """Test that latency is recorded with millisecond precision."""
        revocation_id = revocation.create_revocation_request(
            {
                "subjectType": "user",
                "subjectId": "user-123",
                "scope": "user_access",
            }
        )

        # Small delay
        time.sleep(0.01)  # 10ms

        revocation.mark_revocation_propagated(revocation_id)

        # Check latency
        revocation_record = revocation.get_revocation_status(revocation_id)
        assert revocation_record["propagation_latency_ms"] >= 10

    def test_zero_latency_for_instant_propagation(self):
        """Test that instant propagation shows minimal latency."""
        revocation_id = revocation.create_revocation_request(
            {
                "subjectType": "user",
                "subjectId": "user-123",
                "scope": "user_access",
            }
        )

        # Immediate propagation
        revocation.mark_revocation_propagated(revocation_id)

        # Check latency
        revocation_record = revocation.get_revocation_status(revocation_id)
        # Should be very small (< 100ms for immediate)
        assert revocation_record["propagation_latency_ms"] < 100


class TestRevocationAccessControl:
    """Test that revocations correctly block access."""

    def test_access_blocked_immediately_after_request(self):
        """Test that access is blocked as soon as revocation is requested."""
        # Create revocation (pending state)
        revocation.create_revocation_request(
            {
                "subjectType": "user",
                "subjectId": "user-123",
                "scope": "user_access",
            }
        )

        # Check access before propagation
        is_blocked = revocation.is_subject_revoked("user", "user-123")
        assert is_blocked is True

    def test_access_remains_blocked_after_propagation(self):
        """Test that access stays blocked after propagation completes."""
        # Create and propagate
        revocation_id = revocation.create_revocation_request(
            {
                "subjectType": "user",
                "subjectId": "user-123",
                "scope": "user_access",
            }
        )

        revocation.mark_revocation_propagated(revocation_id)

        # Check access after propagation
        is_blocked = revocation.is_subject_revoked("user", "user-123")
        assert is_blocked is True

    def test_multiple_subjects_revoked_independently(self):
        """Test that revoking one subject doesn't affect others."""
        # Revoke user-1
        revocation.create_revocation_request(
            {
                "subjectType": "user",
                "subjectId": "user-1",
                "scope": "user_access",
            }
        )

        # Check both users
        assert revocation.is_subject_revoked("user", "user-1") is True
        assert revocation.is_subject_revoked("user", "user-2") is False

    def test_different_subject_types_revoked_independently(self):
        """Test that subject types are isolated."""
        # Revoke a user
        revocation.create_revocation_request(
            {
                "subjectType": "user",
                "subjectId": "123",
                "scope": "user_access",
            }
        )

        # Same ID but different type should not be blocked
        assert revocation.is_subject_revoked("user", "123") is True
        assert revocation.is_subject_revoked("integration", "123") is False
