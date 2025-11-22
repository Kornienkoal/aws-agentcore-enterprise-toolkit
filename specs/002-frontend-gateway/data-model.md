# Data Model: Frontend Gateway

## Entities

### InvocationRequest
Payload sent from Streamlit to Gateway to invoke an agent.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | The user's input text. |
| `sessionId` | string | Yes | Unique identifier for the conversation session. |
| `userId` | string | Yes | Unique identifier for the user (sub). |

### AgentListResponse
Response from Gateway listing available agents for the user.

| Field | Type | Description |
|-------|------|-------------|
| `agents` | Array[AgentDescriptor] | List of authorized agents. |

### AgentDescriptor
Metadata about a single agent.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | The agent's unique identifier (e.g., `customer-support`). |
| `name` | string | Display name of the agent. |
| `description` | string | Short description. |

### ErrorResponse
Standard error format.

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Error code (e.g., `Unauthorized`, `AgentNotFound`). |
| `message` | string | Human-readable error message. |
| `requestId` | string | Request ID for tracing. |

## Validation Rules

1. **Token Validation**:
   - Issuer must match Cognito User Pool URL.
   - Audience must match App Client ID.
   - Signature must be valid.
   - Expiration must be in the future.
   - `allowedAgents` claim (custom) or mapped groups must be present.

2. **Access Control**:
   - `POST /agents/{id}/invoke`: The `{id}` must be present in the user's `allowedAgents` list.
