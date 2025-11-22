# Feature Specification: Frontend Gateway Authorization Layer

**Feature Branch**: `frontend-gateway-architecture`
**Created**: 2025-11-19
**Status**: Draft
**Input**: User description: "Introduce an authorization-aware gateway between the Streamlit UI and Bedrock AgentCore. UI authenticates with Cognito Hosted UI, receives tokens containing allowed agents, and calls the new gateway. The gateway validates tokens, checks agent access, and invokes AgentCore with its own IAM role. Gateway should also surface the per-user agent list."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Authenticate and view agents (Priority: P1)

A signed-in customer-support representative uses the Streamlit UI, signs in through Cognito Hosted UI, and expects to see only the agents they are permitted to use in the dropdown.

**Why this priority**: Without surfacing the filtered agent list, users cannot begin any conversation; this is the foundational capability for gated access.

**Independent Test**: Trigger login with a test account assigned to a Cognito group containing two agents and confirm the UI dropdown lists exactly those two agents.

**Acceptance Scenarios**:

1. **Given** a user belongs to Cognito groups `customer-support` and `warranty-docs`, **When** they complete Hosted UI login, **Then** the Streamlit UI dropdown shows both agents and hides any others.
2. **Given** a user belongs to only `customer-support`, **When** they sign in, **Then** the UI renders that single agent pre-selected and disables runtime invocation for any other agent ID.

---

### User Story 2 - Invoke authorized agent session (Priority: P1)

An authorized user selects an allowed agent in the UI and submits a chat message; the gateway validates their token, confirms membership for that agent, and relays the request to the appropriate AgentCore runtime using its IAM role.

**Why this priority**: Enforcing access checks at invocation time prevents privilege escalation via manual API calls and ensures the architecture change delivers its security goal.

**Independent Test**: Attempt to invoke both an allowed agent and a disallowed agent; verify the allowed call succeeds and the disallowed call receives an authorization error without reaching AgentCore.

**Acceptance Scenarios**:

1. **Given** a user token includes `customer-support`, **When** they submit a message to `customer-support`, **Then** the gateway forwards the request to AgentCore and the UI displays the runtime response.
2. **Given** the same token, **When** they attempt to call `warranty-docs`, **Then** the gateway responds with HTTP 403 and logs the denial without invoking AgentCore.

---

### User Story 3 - Session refresh and token reuse (Priority: P2)

A signed-in user returns later, refreshes their access token using the refresh flow, and the gateway continues to honor claims for agent access without forcing reconfiguration.

**Why this priority**: Ensures ongoing sessions remain secure and the architecture supports typical Cognito token lifecycles.

**Independent Test**: Force token refresh via the Streamlit app, capture the new token, and confirm the gateway still accepts allowed agent invocations while rejecting unauthorized ones.

**Acceptance Scenarios**:

1. **Given** a user with a valid refresh token, **When** the Streamlit app exchanges it for a new access token, **Then** the gateway validates the new token’s signature and continues to authorize the same agent set.
2. **Given** the refresh flow returns a token missing the required `allowedAgents` claim, **When** the UI calls the gateway, **Then** the gateway rejects the request with an explicit error indicating missing claims.

---

### Edge Cases

- Token is expired or signature validation fails: gateway returns 401 and instructs the UI to re-authenticate.
- Token includes an agent name that no longer exists in AgentCore: gateway omits it from the list endpoint and logs the mismatch.
- Gateway IAM role loses `bedrock-agentcore` invoke permissions: gateway returns 502/temporary error and raises an operational alert.
- User has no allowed agents claim: UI receives an empty list and displays a guidance message instead of a blank dropdown.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Cognito Hosted UI MUST issue ID and access tokens containing the user’s authorized agents via mapped user groups.
- **FR-002**: Streamlit UI MUST exchange the authorization code, store tokens, and pass the access token to the gateway for all agent-related requests.
- **FR-003**: The new gateway MUST validate Cognito JWTs (signature, expiration, audience, issuer) before processing any request.
- **FR-004**: The gateway MUST expose an endpoint that returns the list of agents filtered to the token’s authorized groups.
- **FR-005**: The gateway MUST prevent invocations to agents not present in the token’s allowed list and return HTTP 403 with a descriptive error.
- **FR-006**: When authorization succeeds, the gateway MUST invoke the corresponding AgentCore runtime using its IAM role via the AWS SDK and return the runtime response to the UI.
- **FR-007**: The gateway MUST log every authorization decision (allow or deny) with user identifier, agent ID, and correlation ID for audit.
- **FR-008**: The gateway MUST surface operational errors from AgentCore to the UI with sanitized messages while preserving correlation IDs for debugging.
- **FR-009**: The Streamlit UI MUST handle empty agent lists by displaying a clear message and disabling chat input.
- **FR-010**: The system MUST support token refresh flows without requiring the user to re-authorize with Cognito, provided the new token retains the required claims.

### Key Entities *(include if feature involves data)*

- **User Token**: Represents the decoded Cognito ID/access token with claims such as `sub`, `email`, and `allowedAgents` (derived from Cognito groups).
- **Agent Descriptor**: Metadata about each AgentCore runtime (name, ARN, status) retrieved via the AgentCore control plane to back the gateway’s listing.
- **Invocation Request**: A structured payload containing `agentId`, `sessionId`, `userId`, and `message` passed from UI to gateway and forwarded to AgentCore upon authorization.

### Assumptions & Dependencies

- Cognito user groups are the canonical source of per-user agent permissions and are managed outside the Streamlit UI.
- The gateway runs on AWS-managed infrastructure with stable outbound access to Bedrock AgentCore control and runtime endpoints in the configured region.
- Streamlit continues to manage PKCE, refresh tokens, and local session storage as implemented in the existing app.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of UI logins show an agent list matching the user’s Cognito group assignments (verified via automated integration tests).
- **SC-002**: Unauthorized agent invocation attempts are blocked with HTTP 403 in under 200 ms without reaching AgentCore, for 99% of requests.
- **SC-003**: Authorized invocations succeed end-to-end (UI → gateway → AgentCore) within 3 seconds for 95% of requests under normal load.
- **SC-004**: Audit logs capture user ID, agent ID, and decision outcome for 100% of gateway requests, enabling post-incident review.
