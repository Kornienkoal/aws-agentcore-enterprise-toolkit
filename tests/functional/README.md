# Functional Tests

Functional tests validate end-to-end workflows using real implementations (no mocks except AWS services).

## Purpose

Unlike unit tests (isolated functions with mocks) and integration tests (component interactions), functional tests verify:
- Complete user workflows across multiple modules
- Real data flows through the system
- API contracts work as documented
- Independent acceptance criteria from user stories

## Structure

```
functional/
├── governance/
│   ├── test_phase1_catalog.py      # US1: Inventory & Ownership
│   ├── test_phase2_authorization.py # US2: Tool Access Governance
│   └── fixtures/
│       ├── sample_principals.yaml   # Test data
│       └── tool_registry.yaml       # Classification data
```

## Running

```bash
# Run all functional tests
uv run pytest tests/functional -v

# Run specific phase
uv run pytest tests/functional/governance/test_phase1_catalog.py -v

# Run with detailed output
uv run pytest tests/functional -vv --tb=short
```

## Test Data

Functional tests use realistic test data from `fixtures/` to simulate production scenarios.

## What Gets Tested

### Phase 1 (US1): Catalog & Ownership
- ✓ Fetch principals from mock IAM
- ✓ Compute least-privilege scores
- ✓ Detect orphan principals
- ✓ Flag inactive principals
- ✓ Compute risk ratings
- ✓ Export catalog snapshot
- ✓ GET /catalog/principals with pagination

### Phase 2 (US2): Authorization
- ✓ Agent-tool mapping CRUD operations
- ✓ Classification enforcement (SENSITIVE requires approval)
- ✓ Authorization decisions with audit trail
- ✓ Differential change tracking
- ✓ GET/PUT /authorization/agents/{agentId}/tools
- ✓ Independent criterion: Remove tool → invocation denied

## Success Criteria

All functional tests must pass before proceeding to next phase.
