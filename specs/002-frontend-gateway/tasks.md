# Tasks: Frontend Gateway Authorization Layer

**Feature Branch**: `002-frontend-gateway-architecture`
**Spec**: [specs/002-frontend-gateway/spec.md](specs/002-frontend-gateway/spec.md)
**Plan**: [specs/002-frontend-gateway/plan.md](specs/002-frontend-gateway/plan.md)

## Phase 1: Setup
**Goal**: Initialize project structure and dependencies for the new gateway service.

- [x] T001 Create service directory structure `services/frontend-gateway/`
- [x] T002 Create `services/frontend-gateway/requirements.txt` with `boto3`, `PyJWT`, `requests`
- [x] T003 Create `services/frontend-gateway/lambda_function.py` skeleton
- [x] T004 Create `infrastructure/terraform/modules/frontend-gateway/` directory structure

## Phase 2: Foundational
**Goal**: Provision core infrastructure and ensure security compliance.

- [x] T005 Remove committed `tfplan` from git history in `infrastructure/terraform/envs/dev/tfplan`
- [x] T006 Create `infrastructure/terraform/modules/frontend-gateway/main.tf` with API Gateway (HTTP API) and Lambda integration
- [x] T007 Create `infrastructure/terraform/modules/frontend-gateway/variables.tf` and `outputs.tf`
- [x] T008 Define IAM role for Gateway Lambda with `bedrock-agentcore:InvokeAgentRuntime` and SSM access in `main.tf`
- [x] T009 Update `infrastructure/terraform/envs/dev/main.tf` to instantiate `frontend-gateway` module
- [x] T010 [P] Create `services/frontend-gateway/auth.py` with JWT validation logic (using `PyJWT`)

## Phase 3: User Story 1 - Authenticate and view agents
**Goal**: Users see only authorized agents in the UI dropdown.

- [x] T011 [US1] Implement `GET /agents` handler in `services/frontend-gateway/lambda_function.py` to return filtered agent list based on token claims
- [x] T012 [US1] Update `frontend/streamlit_app/main.py` to fetch agent list from Gateway URL instead of hardcoded/local config
- [x] T013 [US1] Add `AGENTCORE_GATEWAY_URL` retrieval from SSM in `frontend/streamlit_app/config.py`
- [x] T014 [US1] Verify UI handles empty agent list gracefully in `frontend/streamlit_app/main.py`

## Phase 4: User Story 2 - Invoke authorized agent session
**Goal**: Authorized users can chat with agents via the gateway.

- [x] T015 [US2] Implement `POST /agents/{agentId}/invoke` handler in `services/frontend-gateway/lambda_function.py`
- [x] T016 [US2] Implement AgentCore Runtime invocation via `boto3` in Lambda (proxy logic)
- [x] T017 [US2] Update `frontend/streamlit_app/runtime_client.py` to use `requests` to call Gateway instead of `boto3`
- [x] T018 [US2] Add error handling in `runtime_client.py` for Gateway 403/502 responses

## Phase 5: User Story 3 - Session refresh and token reuse
**Goal**: Long-running sessions remain active via token refresh.

- [x] T019 [US3] Verify `frontend/streamlit_app/auth.py` passes fresh access token to `runtime_client.py` on refresh
- [x] T020 [US3] Ensure Gateway Lambda correctly validates refreshed tokens (standard JWT check)

## Phase 6: Polish & Cross-Cutting
**Goal**: Production readiness, logging, and final cleanup.

- [x] T021 Implement structured logging in `services/frontend-gateway/lambda_function.py` (User ID, Agent ID, Decision)
- [x] T022 Add X-Ray tracing to Gateway Lambda in `infrastructure/terraform/modules/frontend-gateway/main.tf`
- [ ] T023 Run full end-to-end test: Login -> List -> Invoke -> Refresh
- [x] T024 Refactor `frontend/streamlit_app` to `services/frontend_streamlit` to align with new service structure

## Dependencies

1.  **Setup** (T001-T004) must complete first.
2.  **Foundational** (T005-T010) blocks all User Stories.
3.  **US1** (T011-T014) enables the UI to render, blocking US2.
4.  **US2** (T015-T018) depends on US1.
5.  **US3** (T019-T020) can be done in parallel with US2 but logically follows it.

## Parallel Execution Examples

- **Foundational**: T006 (Terraform) and T010 (Auth Logic) can be built in parallel.
- **US1**: T011 (Lambda Handler) and T012 (UI Update) can be developed in parallel if the API contract is agreed upon.

## Implementation Strategy

1.  **Clean & Provision**: Fix the git history issue first, then get the infra up so we have a real URL.
2.  **Auth & List**: Get the "read-only" path working (listing agents). This proves auth is working.
3.  **Invoke**: Add the "write" path (chatting).
4.  **Refine**: Handle edge cases and refresh tokens.
