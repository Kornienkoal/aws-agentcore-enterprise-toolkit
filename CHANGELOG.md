## [Unreleased]

## [2.0.0] - 2025-10-29

### Added
- Project Constitution v2.0.0: template‑first, Terraform‑first, two‑phase deployment model, and
  governance. Source of truth moved to `.specify/memory/constitution.md`.

### Changed
- Contributor guidance (`.github/copilot-instructions.md`) aligned with Constitution v2.0.0:
  Terraform‑based workflows, common pitfalls in HCL, and 5‑minute agent workflow.

### Removed
- Legacy `specs/` artifacts and plans to simplify onboarding and avoid drift from the template.

### Fixed
- Infrastructure teardown completeness: destroy provisioners for Gateway and Memory modules and
  `scripts/infra/teardown.sh` runtime agent deletion via SDK, preventing orphaned AgentCore
  resources on `terraform destroy`.


### Documentation - 2025-10-28

- US2 Complete: Concise stage READMEs with inline Mermaid diagrams and quick starts
  - Infra (Terraform): Prereqs, Quick Start, inline architecture, FAQs
  - Global Tools: Prereqs, Quick Start, inline gateway-tools diagram
  - Agent Runtime: Prereqs, Quick Start, inline runtime diagram
  - Frontend: Prereqs, inline frontend diagram
  - docs index: Added diagram links; status updated to Phase 4
  - Diagrams: Cleaned Mermaid sources (.mmd) and fixed inline blocks in READMEs (moved `flowchart/graph` directive to first line)

### Fixed - 2025-10-28

- Gateway provisioner Lambda now reads identity SSM parameters from `/agentcore/{env}/identity/*` instead of `/{agent_namespace}/{env}/identity/*`.
  - Files: `infrastructure/terraform/custom-resources/agentcore-gateway/lambda_function.py`
  - Impact: Prevents ParameterNotFound/AccessDenied during Gateway creation; aligns with Terraform SSM path convention and IAM policy scope
- Documentation: Replaced placeholder `infrastructure/terraform/README.md` with functional stage documentation and added `docs/diagrams/infra-overview.mmd` diagram.

### Repository Cleanup - 2025-10-28

**Fixed**:
- Fixed `frontend/streamlit_app/pyproject.toml` missing hatch wheel build configuration
  - Added `[tool.hatch.build.targets.wheel]` section with `packages = ["."]`
  - Resolves `uv sync` build failures for Streamlit app
  - **Rationale**: Build system configuration was incomplete, preventing dependency installation

**Validated**:
- Infrastructure (Terraform): All modules validated, no unused resources identified
- Gateway + MCP Tools: Ruff linting passed, both tools (check_warranty, web_search) in active use
- Agent Runtime: All dependencies resolve cleanly, no orphaned code
- Frontend: All Python modules actively imported, no unused static assets

**Summary**:
- Total files reviewed: ~50 across 4 stages
- Files removed: 0
- Files fixed: 1 (pyproject.toml build config)
- Conclusion: Repository is clean and well-maintained; minimal cleanup needed

---

### Phase 6: Native Bedrock AgentCore Integration (Complete)

#### Testing and Automation Infrastructure (2025-01-XX)

**Added**:
- Comprehensive pytest test suites for custom resource Lambdas
  - `infrastructure/terraform/custom-resources/agentcore-gateway/tests/`
    - 15+ test cases covering CREATE/UPDATE/DELETE operations
    - Mock fixtures for CloudFormation events and AWS services
    - SSM parameter storage validation tests
    - Error handling and edge case tests
  - `infrastructure/terraform/custom-resources/agentcore-memory/tests/`
    - 12+ test cases for memory strategies
    - Multi-strategy configuration tests
    - Idempotency validation
  - Test requirements: pytest>=8.0, pytest-cov>=4.1, moto[all]>=5.0
  - TESTING.md with complete guide for running and extending tests

- GitHub Actions CI/CD workflow for custom resources
  - `.github/workflows/test-custom-resources.yml`
  - Automated testing on push/PR to custom-resources/
  - Separate jobs for gateway and memory tests
  - Code coverage reporting with Codecov integration
  - Ruff linting and format checking
  - Python 3.13 runtime matching Lambda environment

- Enhanced automation scripts for Bedrock services
  - Updated `scripts/infra/preflight-checks.sh`:
    - Bedrock AgentCore API access verification
    - Gateway and Memory service quota checks
    - Updated IAM permission requirements
  - Updated `scripts/infra/teardown.sh`:
    - Bedrock Gateway cleanup via Lambda custom resource
    - Bedrock Memory deletion before Terraform destroy
    - Orphaned resource detection for Gateways and Memories
    - Removed legacy API Gateway and DynamoDB checks

**Documentation**:
- Migration guide in `specs/001-provision-shared-infra/quickstart.md`
  - Step-by-step migration from legacy DynamoDB to Bedrock Memory
  - Data export procedures for conversation history
  - Bedrock Gateway migration path from API Gateway
  - Rollback procedures and troubleshooting
  - Post-migration validation checklist
  - 10-step comprehensive migration workflow

- Enhanced observability documentation in `docs/operations-guidelines.md`
  - CloudWatch Dashboard access and navigation
  - Pre-configured dashboard widgets (Gateway, Memory, Errors)
  - Custom dashboard creation examples
  - Pre-configured alarms documentation (5 alarms deployed)
  - SNS topic integration for alert notifications
  - CloudWatch Logs Insights pre-built queries (4 queries)
  - X-Ray tracing and sampling rule configuration
  - Metrics export to S3 and Athena query examples

**Changed**:
- Test requirements now include moto for AWS service mocking
- CI pipeline validates code quality before deployment
- Automation scripts fully aligned with Bedrock-native architecture

**Tasks Completed**:
- T062: ✅ Remove legacy API Gateway resources, extend teardown script
- T063: ✅ Create pytest + moto test suite for gateway custom resource
- T066: ✅ Document DynamoDB to Bedrock Memory migration path
- T070: ✅ Document observability dashboards in operations guide
- T072: ✅ Update automation scripts for Bedrock Gateway and Memory
- T073: ✅ Add CI/CD workflow for custom resource Lambda tests
- T074: ✅ Refresh documentation with new gateway/memory/observability posture

**Phase 6 Status**: 16/16 tasks complete (100%)

#### Runtime Module Update for SDK-Based Agent Deployment (2025-01-XX)

**Added**:
- Bedrock service principal trust policy to runtime IAM role
  - Primary trust: `bedrock.amazonaws.com` (for SDK-based agents)
  - Backward compatibility: `lambda.amazonaws.com` (for migration)
  - Account ID condition prevents cross-account assumption
- Bedrock Gateway invocation permissions
  - Actions: `bedrock-agent:InvokeAgentGateway`, `bedrock-agent:GetAgentGateway`
  - Scoped to agent gateways with matching Environment tag
- Lambda tool invocation permissions
  - Action: `lambda:InvokeFunction`
  - Scoped to tools matching pattern `{agent_namespace}-*-tool-*`
- `log_group_arn` output for SDK integration

**Changed**:
- Runtime module README with comprehensive SDK deployment pattern
  - Example Python code using `bedrock_agentcore` SDK
  - IAM permissions matrix for all policies
  - Memory module integration instructions
  - Migration path from Lambda-based agents
- Runtime role name clarified: `execution-role` (not Lambda-specific)

**Documentation**:
- Created `specs/001-provision-shared-infra/RUNTIME-MODULE-UPDATE.md`
  - Architecture pattern comparison (Lambda vs SDK)
  - SDK deployment example with `AgentBuilder`
  - IAM permissions summary table
  - Testing validation procedures

#### Native Services Migration (2025-10-22)

**Breaking Changes**:
- **BREAKING**: Gateway module replaced API Gateway with Bedrock AgentCore Gateway
  - Removed `cognito_user_pool_arn` variable
  - Changed outputs: `api_id` → `gateway_id`, `invoke_url` (Bedrock endpoint)
  - SSM paths changed: `/gateway/api_id` → `/gateway/gateway_id`
- **BREAKING**: Memory module replaced DynamoDB with Bedrock AgentCore Memory
  - Removed `billing_mode`, `point_in_time_recovery` variables
  - Added `enabled_strategies`, `short_term_ttl_seconds`, `embedding_model_arn`
  - Changed outputs: `table_name` → `memory_id`, `table_arn` → `memory_arn`
  - SSM paths changed: `/memory/table_name` → `/memory/memory_id`

**Added**:
- Lambda custom resource for Bedrock AgentCore Gateway lifecycle management
  - `lambda/custom-resources/agentcore-gateway/lambda_function.py`
  - Powertools instrumentation (structured logging, X-Ray tracing)
  - Idempotent Create/Update/Delete operations
  - SSM parameter storage for gateway identifiers
- Lambda custom resource for Bedrock AgentCore Memory with multi-strategy support
  - `lambda/custom-resources/agentcore-memory/lambda_function.py`
  - Short-term memory (session context with TTL)
  - Long-term memory (user preferences, indefinite retention)
  - Semantic memory (vector embeddings for context retrieval)
  - Configurable embedding models (default: amazon.titan-embed-text-v1)
- CloudWatch metrics and alarms for Bedrock services
  - Gateway latency alarm (default threshold: 5s)
  - Gateway error count alarm (default threshold: 10 errors)
  - Memory throttle detection alarm (default threshold: 5 throttles)
  - Memory read latency alarm (default threshold: 1s)
- CloudWatch dashboard for AgentCore observability
  - Gateway metrics visualization (invocations, errors, p99 latency)
  - Memory metrics visualization (reads, writes, throttles, latency)
  - Recent error logs from agent invocations
- Enhanced validation script for Bedrock services
  - `check_bedrock_gateway()` - Validates Bedrock Gateway accessibility
  - `check_bedrock_memory()` - Validates Memory service accessibility
  - `check_memory_strategies()` - Validates all 3 strategies configured
  - `check_observability_metrics()` - Validates CloudWatch metrics namespace
  - `check_observability_alarms()` - Validates 3 critical alarms exist
  - `check_cloudwatch_dashboard()` - Validates dashboard exists
  - Total validation checks increased from 23 to 28

**Changed**:
- Gateway module (`infrastructure/terraform/modules/gateway/`)
  - Completely rewritten to use Bedrock AgentCore Gateway via custom resource
  - IAM role for Gateway with Lambda invocation permissions
  - Lambda provisioner with Bedrock and SSM permissions
  - `null_resource` for custom resource lifecycle management
- Memory module (`infrastructure/terraform/modules/memory/`)
  - Completely rewritten to use Bedrock AgentCore Memory via custom resource
  - IAM policy for agent access to Bedrock Memory APIs
  - Support for three memory strategies (short/long/semantic)
  - Lambda provisioner with Bedrock, embedding model, and SSM permissions
- Observability module (`infrastructure/terraform/modules/observability/`)
  - Added 4 CloudWatch metric alarms
  - Added CloudWatch dashboard resource
  - Added 10 new SSM parameters for observability settings
  - Enhanced outputs with alarm ARNs and dashboard name
- Validation script (`scripts/infra/validate.sh`)
  - Replaced API Gateway checks with Bedrock Gateway checks
  - Replaced DynamoDB checks with Bedrock Memory checks
  - Added 6 new validation functions for enhanced observability

**Documentation**:
- Added `lambda/custom-resources/agentcore-gateway/README.md` (comprehensive guide)
- Added `lambda/custom-resources/agentcore-memory/README.md` (includes migration guide)
- Added `specs/001-provision-shared-infra/PHASE-6-IMPLEMENTATION-SUMMARY.md` (detailed progress report)

**Remaining Work** (Phase 6 - 44%):
- Update environment overlays (`envs/{dev,staging,prod}/main.tf`) for new module interfaces
- Document DynamoDB to Bedrock Memory migration path in `quickstart.md`
- Update operational documentation with dashboard guide and new service posture
- Extend teardown script for custom resource cleanup
- Create pytest test suites for custom resources (gateway and memory)
- Update CI/CD to run Lambda unit tests

**Tasks Completed**: T059, T060, T061, T064, T065, T067, T068, T069, T071 (9/16 Phase 6 tasks)

**See**: `specs/001-provision-shared-infra/PHASE-6-IMPLEMENTATION-SUMMARY.md` for full details

---

### �🚧 In Progress - Phase 4: Production Readiness (Planning Complete ✅, Implementation Pending)

#### Planning Artifacts (100% Complete)
- ✅ **PHASE-4-PLAN.md**: Strategic overview with 5 major deliverables
  - Testing Framework (pytest, moto, Playwright, Locust)
  - CI/CD Pipeline (GitHub Actions workflows)
  - Monitoring & Observability (CloudWatch, X-Ray, custom metrics)
  - Security Hardening (IAM audit, secret rotation, compliance)
  - Documentation (OpenAPI, runbooks, troubleshooting)
  - 4-week implementation timeline
  - Success criteria: 80% coverage, <5s p95, 0 critical vulns

- ✅ **PHASE-4-TODO.md**: Actionable task breakdown with 150+ checkboxes
  - Complete pytest project structure
  - GitHub Actions workflow templates (4 workflows)
  - CloudWatch dashboard CloudFormation templates
  - X-Ray tracing integration
  - Security audit checklist
  - Documentation requirements

- ✅ **copilot-instructions.md**: Comprehensive developer guide (925+ lines)
  - Architectural principles from architecture-decisions.md
  - IaC-first approach, two-phase deployment, agent-agnostic design
  - Development guidelines: UV, Ruff, pytest, Playwright
  - CloudFormation best practices and CustomResource patterns
  - Agent development workflow and common pitfalls
  - Quality checklist and success criteria

#### Ground Truth Alignment
- ✅ Source of truth: `/Users/kornienkoal/projects/amazon-bedrock-agentcore-samples/01-tutorials/07-AgentCore-E2E/.github/architecture-decisions.md`
- ✅ All 6 architectural decisions incorporated
- ✅ CI/CD strategy: Use toolkit's built-in CodeBuild (optional GitHub Actions)
- ✅ Identity management: IaC-only (no programmatic creation)
- ✅ Deployment workflow: Two-phase (IaC → SDK)
- ✅ Template structure: Three folders (infrastructure, agent-config, agents)
- ✅ CustomResource pattern for AgentCore services

#### Technology Stack Defined
- **Testing**: pytest, pytest-cov, moto[all], Playwright, Locust
- **Code Quality**: Ruff (linting + formatting), mypy (type checking)
- **Security**: bandit, Checkov, Snyk
- **CI/CD**: GitHub Actions, AWS CodeBuild, AWS OIDC
- **Monitoring**: CloudWatch (dashboards + metrics), X-Ray, AWS Config

#### Implementation Readiness
- [ ] Testing framework (Week 1)
- [ ] CI/CD pipeline (Week 2)
- [ ] Monitoring & security (Week 3)
- [ ] Documentation & E2E tests (Week 4)

### ✅ Complete - Phase 3: Infrastructure Templates (100% Complete)
# Changelog

All notable changes to the Amazon Bedrock AgentCore Template will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - 2025-10-21

#### Infrastructure as Code - Terraform Modules (Feature Complete ✅)
Complete Terraform-based infrastructure provisioning system with 6 shared modules and 3 environment overlays.

**Core Modules** (`infrastructure/terraform/modules/`):
- **identity**: Cognito User Pools, M2M OAuth2 client_credentials, resource server with custom scopes
- **gateway**: API Gateway REST API with native Cognito authorizer, /invoke endpoint, X-Ray tracing
- **runtime**: IAM execution roles with least-privilege policies (Bedrock, SSM, CloudWatch, DynamoDB)
- **memory**: DynamoDB tables with partition key isolation (`{env}#{agent}#{user_id}`), TTL support
- **knowledge**: Optional Bedrock Knowledge Base with S3 data source, OpenSearch Serverless vector storage, embedding models
  ⚠️ **Note**: AWS S3 Vectors is preferred but not yet supported in Terraform AWS provider v5.100.0 (S3 Vectors in preview as of Oct 2025). Will migrate when provider support is available.
- **observability**: CloudWatch Log Groups (invocations/tools/API), X-Ray sampling rules, optional KMS encryption

**Environment Overlays** (`infrastructure/terraform/envs/{dev,staging,prod}/`):
- Dev: Optional MFA, 7-day log retention, no encryption, 100% X-Ray sampling
- Staging: ON MFA, 30-day retention, encryption enabled, 50% X-Ray sampling
- Prod: ON MFA, 90-day retention, encryption enabled, 10% X-Ray sampling

**Shared Infrastructure** (`infrastructure/terraform/modules/_shared/`):
- Common locals for tagging (Environment, AgentNamespace, Component, ManagedBy)
- Naming conventions: `{namespace}-{component}-{env}`
- SSM parameter paths: `/agentcore/{env}/{component}/*`

**Global Configuration** (`infrastructure/terraform/globals/`):
- `backend.tfvars`: S3 backend with DynamoDB locking, encryption at rest
- `tagging.tfvars`: Default tags (Project, ManagedBy, CostCenter)

**Operational Scripts** (`scripts/infra/`):
- `validate.sh`: Post-deployment validation (9 component checks)
- `teardown.sh`: Safe infrastructure destruction with production safeguards
- `drift-check.sh`: Configuration drift detection using `terraform plan -detailed-exitcode`
- `noop-check.sh`: CI-friendly idempotency validation
- `preflight-checks.sh`: Pre-deployment validation (8 checks: credentials, tools, quotas, IAM, backend, network)
- `terraform-validate.sh`: Comprehensive validation (fmt, validate, lint)

**Agent Consumption** (`agent-config/`, `docs/`):
- `agent-config/sample-agent.yaml`: Template showing SSM parameter consumption pattern
- `docs/agent-onboarding.md`: 5-minute developer onboarding guide with SSM reference table
- `scripts/agents/smoke-test.sh`: Agent infrastructure access validation (9 tests)

**Documentation** (`docs/`, `specs/`):
- `specs/001-provision-shared-infra/quickstart.md`: Complete deployment guide
- `docs/operations-guidelines.md`: Operational runbook (deployment workflows, drift remediation, rollback procedures, monitoring, security, troubleshooting)
- `CONTRIBUTING.md`: Terraform development workflow, CI/CD integration, pre-commit hooks, security checklist

**Quality & Security**:
- IAM least-privilege policies with explicit ARNs (wildcards documented where required by AWS)
- All tagging across all 6 modules using shared locals
- SSM Parameter Store for all module outputs (23 parameters total)
- Pre-commit hooks for terraform fmt/validate/tflint
- GitHub Actions CI/CD workflow examples (validate, plan, deploy with manual approval)

**Architecture Compliance**:
- ✅ IaC-first approach (Terraform > SDK)
- ✅ Agent-agnostic design (shared infrastructure for unlimited agents)
- ✅ AWS native services (Cognito native authorizer, no custom Lambda auth)
- ✅ Two-phase deployment (IaC infrastructure → SDK agent runtime)
- ✅ Least-privilege IAM with scoped resources
- ✅ Production hardening (MFA, encryption, log retention, X-Ray)
