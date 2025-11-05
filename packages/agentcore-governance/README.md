# AgentCore Governance Package

**Enterprise Security Role & Token Audit and Control Model**

The `agentcore-governance` package delivers a comprehensive governance framework for AWS Bedrock AgentCore deployments, providing visibility, control, and auditability across IAM principals, tool authorization, third-party integrations, and emergency revocation workflows.

## Overview

This package implements five core user stories with production-ready capabilities:

1. **Inventory & Ownership Visibility (US1)**: Catalog aggregation with inactivity flagging and risk scoring
2. **Tool Access Governance (US2)**: Per-agent tool authorization with classification enforcement
3. **Third-Party Integration Onboarding (US3)**: Static allowlist workflow with request/approval/expiry
4. **Rapid Revocation (US4)**: Emergency token revocation with SLA tracking
5. **Audit Trace Reconstruction (US5)**: End-to-end correlation chain reconstruction with evidence packs

---

## Architecture

```
src/agentcore_governance/
├── api/                    # REST API handlers
│   ├── catalog_handlers.py
│   ├── authorization_handlers.py
│   ├── integration_handlers.py
│   ├── revocation_handlers.py
│   ├── decision_handlers.py
│   ├── analyzer_handlers.py
│   └── evidence_handlers.py
├── analyzer.py             # Least-privilege scoring & risk aggregation
├── authorization.py        # Agent-to-tool authorization mapping
├── catalog.py              # Principal catalog aggregation (IAM, SSM, tags)
├── classification.py       # Tool classification registry (SENSITIVE, RESTRICTED, STANDARD)
├── evidence.py             # Audit event construction & integrity verification
├── integrations.py         # Third-party integration registry & approval
├── revocation.py           # Emergency revocation workflow & SLA tracking
├── correlation.py          # Correlation ID generation & propagation
├── integrity.py            # Deterministic SHA256 hash utilities
├── abac_matrix.py          # ABAC feasibility matrix exporter
└── __init__.py
```

---

## Getting Started

### Installation

```bash
# Install package with dependencies
uv sync  # or: pip install -e packages/agentcore-governance

# Run tests
uv run pytest tests/unit/governance -v
uv run pytest tests/integration/governance -v
```

### Quick Start (Local Development)

```python
from agentcore_governance.catalog import fetch_principal_catalog, flag_inactive_principals
from agentcore_governance.analyzer import enrich_principals_with_scores

# 1. Fetch principal catalog
principals = fetch_principal_catalog(environments=["dev"])

# 2. Flag inactive principals (> 30 days unused)
principals = flag_inactive_principals(principals, inactivity_threshold=30)

# 3. Enrich with least-privilege scores and risk ratings
principals = enrich_principals_with_scores(principals)

# 4. Export snapshot
from agentcore_governance.catalog import export_catalog_snapshot
snapshot = export_catalog_snapshot(principals, environment="dev")
```

---

## Core Workflows

### Workflow 1: Inventory & Risk Assessment

**Goal**: Identify high-risk principals and orphan resources

```python
from agentcore_governance.catalog import fetch_principal_catalog, flag_inactive_principals
from agentcore_governance.analyzer import enrich_principals_with_scores, detect_orphan_principals

# Fetch and enrich principals
principals = fetch_principal_catalog()
principals = flag_inactive_principals(principals, inactivity_threshold=30)
principals = enrich_principals_with_scores(principals)

# Detect orphaned principals (missing owner/purpose)
orphans = detect_orphan_principals(principals)
print(f"Found {len(orphans)} orphaned principals requiring ownership assignment")

# Identify high-risk principals
high_risk = [p for p in principals if p["risk_rating"] == "HIGH"]
print(f"Found {len(high_risk)} HIGH risk principals requiring review")
```

### Workflow 2: Tool Authorization Management

**Goal**: Control agent tool access with classification enforcement

```python
from agentcore_governance.authorization import set_authorized_tools, check_tool_authorized
from agentcore_governance.classification import load_classification_registry, check_access_allowed

# Load tool classification registry
classification_registry = load_classification_registry("security/tool-classification.yaml")

# Authorize tools for agent
agent_id = "customer-support-agent-v1"
tools = ["get_product_info", "search_documentation", "check_warranty"]
change_report = set_authorized_tools(agent_id, tools, reason="Initial provisioning")

# Check authorization with classification enforcement
approval_record = None  # Would be fetched from approval system
allowed = check_access_allowed(
    tool_id="sensitive_tool",
    classification_registry=classification_registry,
    approval_record=approval_record
)
```

### Workflow 3: Third-Party Integration Approval

**Goal**: Manage external API integrations with expiry

```python
from agentcore_governance.integrations import request_integration, approve_integration, check_integration_allowed

# Request integration
request = request_integration(
    integration_name="HubSpot CRM",
    requester="team-lead@company.com",
    scope=["crm:read", "contacts:read"],
    justification="Customer support ticket enrichment"
)

# Approve with expiry
approval = approve_integration(
    integration_id=request["integration_id"],
    approver="security-admin@company.com",
    expiry_days=90
)

# Check access
allowed = check_integration_allowed(request["integration_id"], target_endpoint="https://api.hubapi.com")
```

### Workflow 4: Emergency Revocation

**Goal**: Rapidly revoke compromised tokens with SLA tracking

```python
from agentcore_governance.revocation import initiate_revocation, track_revocation_status

# Initiate revocation
revocation = initiate_revocation(
    principal_id="arn:aws:iam::123456789012:role/CompromisedRole",
    reason="Security incident - credential leak detected",
    targets=["bedrock", "lambda", "s3"]
)

# Track propagation
status = track_revocation_status(revocation["revocation_id"])
print(f"Revocation status: {status['status']} ({status['elapsed_seconds']}s elapsed)")
```

### Workflow 5: Audit Trace Reconstruction

**Goal**: Reconstruct complete event chain for compliance audits

```python
from agentcore_governance.evidence import reconstruct_correlation_chain, generate_evidence_pack

# Reconstruct event chain
correlation_id = "req-abc123-def456"
chain = reconstruct_correlation_chain(correlation_id)

print(f"Reconstructed {len(chain['events'])} events")
print(f"Chain integrity: {'VALID' if chain['integrity_valid'] else 'TAMPERED'}")
print(f"Total latency: {chain['latency_ms']}ms")

# Generate evidence pack
evidence_pack = generate_evidence_pack(hours_back=24, include_metrics=True)
print(f"Evidence pack contains {evidence_pack['summary']['total_decisions']} decisions")
```

---

## API Endpoints

### Catalog Endpoints

- `GET /catalog/principals`: List all principals with pagination, filtering, and risk flags
- `GET /catalog/principals/{principalId}`: Retrieve specific principal details
- `POST /catalog/export`: Export catalog snapshot as JSON

### Authorization Endpoints

- `GET /authorization/agents/{agentId}/tools`: List authorized tools for agent
- `PUT /authorization/agents/{agentId}/tools`: Update tool authorization with differential reporting
- `GET /authorization/differential/{agentId}`: View authorization change history

### Integration Endpoints

- `POST /integrations`: Request new third-party integration
- `GET /integrations/{integrationId}`: Retrieve integration details
- `POST /integrations/{integrationId}/approve`: Approve integration with expiry
- `GET /integrations/{integrationId}/status`: Check approval status and expiry

### Revocation Endpoints

- `POST /revocations`: Initiate emergency revocation
- `GET /revocations/{revocationId}`: Track revocation status and SLA compliance
- `GET /revocations/active`: List all active revocations

### Decision & Evidence Endpoints

- `GET /decisions`: List policy decisions with filtering (subject, effect, resource, action, time)
- `GET /decisions?aggregate_by=subject_id`: Aggregate decisions by dimension
- `GET /analyzer/least-privilege`: Generate least-privilege conformance report
- `GET /analyzer/risk-aggregation`: Enterprise-wide risk metrics
- `POST /evidence-pack`: Generate comprehensive evidence pack for audits
- `GET /evidence-pack/{correlationId}`: Reconstruct correlation chain

---

## Advanced Features

### Differential Policy Change Reporting (FR-019)

```python
from agentcore_governance.analyzer import generate_policy_change_report

before_snapshot = export_catalog_snapshot(principals, environment="prod")
# ... time passes, policies change ...
after_snapshot = export_catalog_snapshot(principals, environment="prod")

change_report = generate_policy_change_report(before_snapshot["principals"], after_snapshot["principals"])
print(f"Added: {change_report['summary']['added_count']}")
print(f"Removed: {change_report['summary']['removed_count']}")
print(f"Modified: {change_report['summary']['modified_count']}")
```

### Risk Scoring Aggregation (FR-021)

```python
from agentcore_governance.analyzer import aggregate_risk_scores

risk_metrics = aggregate_risk_scores(principals)
print(f"High-risk principals: {risk_metrics['risk_distribution']['HIGH']}")
print(f"Average LP score: {risk_metrics['average_least_privilege_score']}")
for rec in risk_metrics['recommendations']:
    print(f"⚠️  {rec}")
```

### Quarterly Attestation Scheduling (FR-018)

```python
from agentcore_governance.catalog import schedule_quarterly_attestation

attestation = schedule_quarterly_attestation(
    owner="team-lead@company.com",
    principals=[p for p in principals if p.get("owner") == "team-lead@company.com"]
)
print(f"Attestation {attestation['attestation_id']} scheduled for {attestation['scheduled_date']}")
```

### Deprecated Tool Cleanup

```python
from agentcore_governance.authorization import cleanup_deprecated_tools

summary = cleanup_deprecated_tools(
    tool_id="legacy_search_v1",
    deprecation_date="2024-01-01T00:00:00Z",
    notify_agents=True
)
print(f"Removed from {summary['removal_count']} agents: {summary['affected_agents']}")
```

### ABAC Feasibility Export

```python
from agentcore_governance.abac_matrix import generate_default_abac_matrix, export_abac_csv_file

matrix = generate_default_abac_matrix()
export_abac_csv_file(matrix["attributes"], "abac-matrix.csv")
```

---

## Testing

### Unit Tests

```bash
# Run all unit tests
uv run pytest tests/unit/governance -v

# Run specific test module
uv run pytest tests/unit/governance/test_analyzer_scoring.py -v
```

### Integration Tests

```bash
# Run all integration tests
uv run pytest tests/integration/governance -v

# Run specific user story tests
uv run pytest tests/integration/governance/test_catalog_endpoint.py -v
uv run pytest tests/integration/governance/test_authorization_endpoints.py -v
```

### Test Coverage

```bash
uv run pytest tests/unit/governance tests/integration/governance --cov=src/agentcore_governance --cov-report=html
```

---

## Configuration

### Tool Classification Registry

Define tool sensitivity levels in `security/tool-classification.yaml`:

```yaml
tools:
  - id: get_product_info
    name: Product Information Lookup
    sensitivity: STANDARD
    requires_approval: false

  - id: check_warranty
    name: Warranty Status Check
    sensitivity: SENSITIVE
    requires_approval: true
    approval_ttl_days: 90

  - id: delete_customer_data
    name: Customer Data Deletion
    sensitivity: RESTRICTED
    requires_approval: true
    approval_ttl_days: 30
```

### Environment Variables

```bash
# AWS credentials for IAM/SSM access
export AWS_REGION=us-east-1
export AWS_PROFILE=agentcore-governance

# Logging configuration
export LOG_LEVEL=INFO
export LOG_FORMAT=json
```

---

## Observability

### CloudWatch Metrics

Key metrics emitted for monitoring:

- `governance.decisions.count`: Total policy decisions
- `governance.decisions.denied`: Denied access attempts
- `governance.revocations.sla_ms`: Revocation propagation latency
- `governance.principals.high_risk_count`: High-risk principal count
- `governance.conformance.score`: Least-privilege conformance score

### X-Ray Tracing

All API handlers support X-Ray tracing with correlation IDs for end-to-end trace reconstruction.

### Audit Logs

All governance operations emit structured CloudWatch Logs with:
- Correlation ID for tracing
- Integrity hash for tamper detection
- Timestamp and principal metadata
- Action and outcome details

---

## Troubleshooting

### Common Issues

**Q: Catalog aggregation fails with IAM permission errors**
A: Ensure the execution role has `iam:ListRoles`, `iam:ListRoleTags`, and `iam:ListAttachedRolePolicies` permissions.

**Q: Evidence pack generation is slow**
A: Reduce `hours_back` parameter or enable CloudWatch Insights for faster log aggregation.

**Q: Risk ratings show all principals as HIGH**
A: Check that principals have valid `policy_summary` with wildcard counts. Run `enrich_principals_with_scores()` after catalog fetch.

**Q: Orphan detection flags valid principals**
A: Ensure principals have `Owner` and `Purpose` tags in IAM. Use `owner` and `purpose` keys in tag metadata.

---

## Contributing

See `CONTRIBUTING.md` for development guidelines. Key points:

- Run `uv run ruff check .` before committing
- Add tests for new features (unit + integration)
- Update this README for new workflows
- Follow OpenAPI contract in `specs/001-security-role-audit/contracts/openapi.yaml`

---

## References

- **Specification**: `specs/001-security-role-audit/spec.md`
- **Data Model**: `specs/001-security-role-audit/data-model.md`
- **API Contract**: `specs/001-security-role-audit/contracts/openapi.yaml`
- **Tasks & Phases**: `specs/001-security-role-audit/tasks.md`
- **Quickstart Guide**: `specs/001-security-role-audit/quickstart.md`

---

## License

See `LICENSE` in repository root.
