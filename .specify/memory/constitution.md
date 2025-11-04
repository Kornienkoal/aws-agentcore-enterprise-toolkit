<!--
Sync Impact Report

- Version change: 1.0.3 → 2.0.0
- Modified principles (mapping):
	- "Use AWS Native Services First" → kept (clarified for template mission)
	- "Infrastructure as Code with Terraform" → kept (expanded with module and state conventions)
	- "Authentication & Authorization" → merged into "Security & Identity by Default"
	- "Agent‑Agnostic, Shared Infrastructure" → kept (reframed as "Template‑Agnostic, Multi‑Agent")
	- "Quality Gates: Test/Observability/Security" → split into "Testing Discipline" and "Observability & Reliability"
- Added sections:
	- Template Mission & 5‑minute Agent Workflow
	- Two‑Phase Deployment Model (Terraform → Agent code)
	- Documentation & Onboarding Discipline
- Removed sections:
	- None (constraints reorganized under Principles and NFRs)
- Templates reviewed:
	- .specify/templates/plan-template.md → ✅ aligns; Constitution Check derives from this document
	- .specify/templates/spec-template.md → ✅ generic; no changes
	- .specify/templates/tasks-template.md → ✅ generic; no changes
	- .specify/templates/commands/* → ⚠ reference in plan-template mentions commands folder; directory not found. TODO add commands or update note.
- Follow-ups / Deferred:
	- TODO(COMMAND_TEMPLATES): Create `.specify/templates/commands/plan.md` (and related) or adjust plan-template note.
	- TODO(QUICKSTART): Ensure docs/quickstart or specs/* quickstarts reflect the 5‑minute agent workflow verbatim.
-->

# Amazon Bedrock Agent Template Constitution

This repository is a production‑grade template for building agents on Amazon Bedrock AgentCore.
Its purpose is to let teams create a new agent in minutes, on top of shared, secure, and
observed infrastructure — with one‑command deployment and repeatable operations.

## Template Mission and Outcomes

- Accelerate new agent creation to under 5 minutes from template.
- Provision once, support many agents (agent‑agnostic core).
- Provide end‑to‑end automation (provision → deploy → observe → teardown).
- Enforce security, reliability, and cost discipline by default.

## Core Principles

### P1. Template‑First, Opinionated Defaults
The template MUST provide ready‑to‑run defaults: wiring, permissions, and examples that work out of
the box. Customization points MUST be explicit and minimal, with clear guards against foot‑guns.

Rationale: Opinionated defaults are the fastest path to a working, secure agent.

### P2. Prefer AWS‑Native Services
Use AWS‑managed capabilities whenever available (Cognito, API Gateway authorizers, SSM Parameter
Store, DynamoDB, CloudWatch, X‑Ray). Avoid custom Lambdas for concerns already covered natively.

Rationale: Native services reduce latency, cost, complexity, and operational burden.

### P3. Infrastructure via Terraform Only (No SDK Provisioning)
All infrastructure MUST be declared with Terraform modules. Application code MUST NOT create or
mutate infrastructure via SDK. Persist essential identifiers in SSM under a parameterized path:

```
/{agent_namespace}/agentcore/{component}/...
/{agent_namespace}/agentcore/agents/{agent}/...  # only when per‑agent data is required
```

Rationale: Guarantees repeatability, reviewability, environment parity, and clean teardown.

### P4. Two‑Phase Deployment Model
1) Phase 1: Provision shared infrastructure via Terraform (identity, gateway, memory, runtime
	 scaffolding, optional knowledge base). 2) Phase 2: Deploy agent code and configuration via the
	 official toolkit/SDK. Deleting follows the same phases in reverse.

Rationale: Separates platform lifecycle from agent iteration velocity.

### P5. Template‑Agnostic, Multi‑Agent Infrastructure
Core services (Gateway tools, Memory, Runtime scaffolding) are provisioned once and shared across
agents. Adding an agent MUST NOT require changing shared stacks. Agents load configuration from
YAML and resolve secrets/IDs from SSM.

Rationale: Enables scale — many agents, one platform.

### P6. Security & Identity by Default
- Inside AWS: Use IAM with SigV4; no long‑lived credentials.
- Frontend: Cognito Hosted UI with Authorization Code + PKCE.
- External M2M: Prefer Cognito client_credentials. Lambda authorizers only when unavoidable.
- IAM: Least privilege, no wildcards, resource policies on tool Lambdas.
- Data: Memory isolation by env/agent/user using partition keys and IAM conditions.

Rationale: Security must be built‑in, not bolted‑on.

### P7. Observability & Reliability
Enable structured logging, metrics, and X‑Ray tracing for runtimes and tools. Surface operational
dashboards and alerts for critical paths. Establish SLOs with p95 latency < 5s and error rate < 1%.

Rationale: Fast iteration requires deep visibility.

### P8. Testing Discipline & Quality Gates
- Unit/integration tests required for shared packages and agent code; target ≥80% coverage.
- Lint and format with ruff; type‑check with mypy for Python.
- IaC checks: terraform fmt/validate/plan; run cfn‑lint for embedded CloudFormation if present.

Rationale: Prevent regressions and ensure maintainability.

### P9. Documentation & Onboarding
Maintain a 5‑minute “Add a New Agent” guide and end‑to‑end quickstart. Keep docs synchronized with
Terraform outputs and SSM conventions. Every customization point must be documented.

Rationale: The template’s value is measured by how quickly others can succeed.

### P10. Versioning & Backwards Compatibility
Follow semantic versioning for shared libraries and this constitution. Breaking changes to template
APIs, directory structure, or mandatory workflows require a MAJOR bump and migration notes.

Rationale: Predictable upgrades enable adoption.

## Non‑Functional Requirements

- Performance: p95 < 5s; error rate < 1% under nominal load.
- Environment Parity: dev/staging/prod use identical modules; differences only via variables.
- Cost Awareness: Prefer serverless and pay‑per‑request; remove idle resources by default.

## Workflow and Merge Gates

Teams MUST follow: Analyse → Plan → Confirm → Change → Test → Analyse Again.

Merge is blocked unless all are true:
- Tests pass (unit/integration/E2E as applicable)
- Lint, format, and type checks pass
- Terraform validated and plans reviewed
- Security review completed for IAM/policies/secrets changes

## Governance

1. Supremacy: This document governs engineering practice for the template.
2. Amendments: PRs must include rationale, impact analysis, and version bump proposal.
	 - MAJOR: breaking governance or template contract changes
	 - MINOR: new principle/section or materially expanded guidance
	 - PATCH: clarifications and non‑semantic edits
3. Compliance: Reviews MUST verify adherence to P1–P10. Deviations require explicit justification
	 and tracked remediation tasks.
4. Records: Keep state backends, SSM conventions, and identity decisions in docs; update when this
	 constitution changes.

**Version**: 2.0.0 | **Ratified**: 2025-10-21 | **Last Amended**: 2025-10-29
