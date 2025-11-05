"""Functional tests for Phase 1 (US1): Inventory & Ownership Visibility.

Tests the complete catalog workflow end-to-end using real implementations.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from agentcore_governance import analyzer, catalog
from agentcore_governance.api import catalog_handlers


class TestPhase1CatalogWorkflow:
    """End-to-end tests for catalog and ownership features."""

    def test_fetch_and_analyze_principals(self, sample_principals: list[dict]) -> None:
        """Fetch principals, compute scores, detect orphans, flag inactive."""
        # Use sample_principals directly (fetch_principal_catalog uses boto3 internally)
        principals = sample_principals
        assert len(principals) == 6
        assert all("arn" in p for p in principals)

        # Compute least-privilege scores for all principals
        for principal in principals:
            score = analyzer.compute_least_privilege_score(principal)
            assert 0.0 <= score <= 1.0

            # Verify scoring logic
            if principal["name"] == "customer-support-agent-dev":
                assert score == 1.0  # Perfect score: no wildcards

            if principal["name"] == "legacy-admin-role":
                assert score < 0.5  # Poor score: wildcard actions + resources

        # Detect orphans
        orphans = analyzer.detect_orphan_principals(principals)
        orphan_names = {p["name"] for p in orphans}
        assert "orphan-test-role" in orphan_names  # Missing Owner
        assert "legacy-admin-role" in orphan_names  # Missing Owner and Purpose
        assert "customer-support-agent-dev" not in orphan_names  # Has Owner

        # Flag inactive principals (90 day threshold)
        flagged = catalog.flag_inactive_principals(principals, inactivity_days=90)
        flagged_names = {p["name"] for p in flagged}
        assert "legacy-admin-role" in flagged_names  # Last used 2024-08-15
        assert "unused-role" in flagged_names  # Never used
        assert "customer-support-agent-prod" not in flagged_names  # Used 2025-11-05

    def test_compute_risk_ratings(self, sample_principals: list[dict]) -> None:
        """Compute risk ratings for all principals."""
        for principal in sample_principals:
            rating = analyzer.compute_risk_rating(principal, inactivity_days=90)
            assert rating in ["low", "moderate", "high"]

            # Verify risk logic
            if principal["name"] == "customer-support-agent-dev":
                assert rating == "low"  # Perfect score, active, has owner

            if principal["name"] == "legacy-admin-role":
                assert rating == "high"  # Wildcards + inactive + orphan

            if principal["name"] == "warranty-docs-agent-staging":
                # Has wildcard resources but active and has owner
                assert rating in ["low", "moderate"]

    def test_export_catalog_snapshot(self, sample_principals: list[dict]) -> None:
        """Export complete catalog snapshot with all analysis."""
        mock_iam = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Roles": sample_principals}]
        mock_iam.get_paginator.return_value = mock_paginator

        # Export snapshot
        snapshot = catalog.export_catalog_snapshot(mock_iam, inactivity_days=90)

        # Verify snapshot structure
        assert "timestamp" in snapshot
        assert "total_principals" in snapshot
        assert "principals" in snapshot
        assert "summary" in snapshot

        # Verify counts
        assert snapshot["total_principals"] == 6
        assert len(snapshot["principals"]) == 6

        # Verify summary
        summary = snapshot["summary"]
        assert "orphan_count" in summary
        assert "inactive_count" in summary
        assert "risk_distribution" in summary

        # Verify each principal has enriched data
        for p in snapshot["principals"]:
            assert "arn" in p
            assert "least_privilege_score" in p
            assert "is_orphan" in p
            assert "is_inactive" in p
            assert "risk_rating" in p

    def test_catalog_endpoint_with_pagination(self, sample_principals: list[dict]) -> None:
        """Test GET /catalog/principals endpoint with pagination."""
        mock_iam = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Roles": sample_principals}]
        mock_iam.get_paginator.return_value = mock_paginator

        # Test first page (page_size=3)
        response = catalog_handlers.get_principals(
            iam_client=mock_iam,
            environments=None,
            owner=None,
            page=1,
            page_size=3,
        )

        assert response["success"] is True
        assert len(response["principals"]) == 3
        assert response["pagination"]["total_count"] == 6
        assert response["pagination"]["page"] == 1
        assert response["pagination"]["page_size"] == 3
        assert response["pagination"]["total_pages"] == 2

        # Test second page
        response = catalog_handlers.get_principals(
            iam_client=mock_iam,
            environments=None,
            owner=None,
            page=2,
            page_size=3,
        )

        assert response["success"] is True
        assert len(response["principals"]) == 3
        assert response["pagination"]["page"] == 2

    def test_catalog_endpoint_with_filters(self, sample_principals: list[dict]) -> None:
        """Test catalog endpoint with environment and owner filters."""
        mock_iam = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Roles": sample_principals}]
        mock_iam.get_paginator.return_value = mock_paginator

        # Filter by environment=dev
        response = catalog_handlers.get_principals(
            iam_client=mock_iam,
            environments=["dev"],
            owner=None,
            page=1,
            page_size=100,
        )

        assert response["success"] is True
        dev_principals = response["principals"]
        assert all(
            p.get("tags", {}).get("Environment") == "dev" for p in dev_principals if p.get("tags")
        )

        # Filter by owner=platform-team
        response = catalog_handlers.get_principals(
            iam_client=mock_iam,
            environments=None,
            owner="platform-team",
            page=1,
            page_size=100,
        )

        assert response["success"] is True
        owner_principals = response["principals"]
        assert all(
            p.get("tags", {}).get("Owner") == "platform-team"
            for p in owner_principals
            if p.get("tags")
        )

    def test_ownership_validation_and_fallback(self, sample_principals: list[dict]) -> None:
        """Test ownership validation with UNASSIGNED fallback."""
        mock_iam = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Roles": sample_principals}]
        mock_iam.get_paginator.return_value = mock_paginator

        response = catalog_handlers.get_principals(
            iam_client=mock_iam,
            environments=None,
            owner=None,
            page=1,
            page_size=100,
        )

        principals = response["principals"]

        # Verify ownership assignment
        for p in principals:
            assert "owner" in p
            if p["name"] == "customer-support-agent-dev":
                assert p["owner"] == "platform-team"
            elif p["name"] == "orphan-test-role" or p["name"] == "legacy-admin-role":
                assert p["owner"] == "UNASSIGNED"  # Missing Owner tag


class TestPhase1AcceptanceCriteria:
    """Verify independent acceptance criteria for Phase 1 (US1)."""

    def test_independent_criterion_ownership_flagging(self, sample_principals: list[dict]) -> None:
        """Independent criterion: Fetch catalog → orphan principals flagged with owner=UNASSIGNED."""
        mock_iam = MagicMock()
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [{"Roles": sample_principals}]
        mock_iam.get_paginator.return_value = mock_paginator

        # Fetch catalog
        response = catalog_handlers.get_principals(
            iam_client=mock_iam,
            environments=None,
            owner=None,
            page=1,
            page_size=100,
        )

        principals = response["principals"]

        # Find orphan-test-role (missing Owner tag)
        orphan = next(p for p in principals if p["name"] == "orphan-test-role")
        assert orphan["owner"] == "UNASSIGNED"
        assert orphan["is_orphan"] is True

        # Find legacy-admin-role (missing Owner and Purpose)
        legacy = next(p for p in principals if p["name"] == "legacy-admin-role")
        assert legacy["owner"] == "UNASSIGNED"
        assert legacy["is_orphan"] is True

        # Find customer-support-agent-dev (has Owner)
        valid = next(p for p in principals if p["name"] == "customer-support-agent-dev")
        assert valid["owner"] == "platform-team"
        assert valid["is_orphan"] is False
