# Implementation Plan: Frontend Gateway Authorization Layer

**Branch**: `002-frontend-gateway-architecture` | **Date**: 2025-11-22 | **Spec**: [specs/002-frontend-gateway/spec.md](specs/002-frontend-gateway/spec.md)
**Input**: Feature specification from `/specs/002-frontend-gateway/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Introduce an authorization-aware gateway between the Streamlit UI and Bedrock AgentCore. The gateway (API Gateway + Lambda) validates Cognito tokens, enforces agent access based on claims, and proxies authorized requests to the AgentCore Runtime.

## Technical Context

**Language/Version**: Python 3.13 (Lambda), Terraform (Infra)
**Primary Dependencies**: `boto3`, `PyJWT` (JWT validation), `requests` (Streamlit client)
**Storage**: N/A (Stateless)
**Testing**: `pytest`, `moto`
**Target Platform**: AWS Lambda, API Gateway (HTTP API)
**Project Type**: Web application (Frontend + Backend Gateway)
**Performance Goals**: p95 < 3s
**Constraints**: p95 < 5s, error rate < 1%
**Scale/Scope**: Multi-agent support

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **P1. Template-First**: Compliant. Adding standard module.
- **P2. AWS-Native**: Compliant. Using API Gateway + Lambda.
- **P3. Terraform Only**: Compliant. All infra in Terraform.
- **P4. Two-Phase**: Compliant. Infra first, then code.
- **P5. Multi-Agent**: Compliant. Gateway is generic.
- **P6. Security**: Compliant. Cognito + IAM SigV4.
- **P7. Observability**: Compliant. X-Ray/Logs.
- **P8. Testing**: Compliant. Tests included.

## Project Structure

### Documentation (this feature)

```
specs/002-frontend-gateway/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```
infrastructure/
└── terraform/
    └── modules/
        └── frontend-gateway/  # New Terraform module

services/
└── frontend-gateway/          # New Lambda code
    ├── lambda_function.py
    ├── auth.py
    └── requirements.txt

frontend/
└── streamlit_app/
    ├── runtime_client.py      # Updated to use Gateway
    └── main.py                # Updated to fetch agent list
```

**Structure Decision**: Create `services/frontend-gateway` for the Lambda code and `infrastructure/terraform/modules/frontend-gateway` for the infrastructure. This separates the gateway service from specific agents and shared packages.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | | |
