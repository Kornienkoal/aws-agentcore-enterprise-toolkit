# Research: Frontend Gateway Authorization Layer

## Decisions

### 1. Architecture: API Gateway (HTTP API) + Lambda Proxy
**Decision**: Deploy an Amazon API Gateway (HTTP API) backed by a single Python Lambda function ("Monolithic" Gateway).
**Rationale**:
- **Simplicity**: HTTP API is cheaper and faster than REST API. A single Lambda handles both "list agents" and "invoke agent" logic, sharing the Cognito token validation code.
- **Security**: The Lambda validates the JWT `allowedAgents` claim before making any calls to AgentCore. It assumes a specific IAM role with `bedrock-agentcore:InvokeAgentRuntime` permission, keeping the frontend client (Streamlit) decoupled from AWS IAM permissions.
- **Filtering**: The Lambda can filter the list of agents based on the user's token claims, satisfying FR-004.

### 2. Code Location: `services/frontend-gateway`
**Decision**: Place the gateway Lambda code in a new top-level directory `services/frontend-gateway`.
**Rationale**:
- The `agents/` directory is for specific agents.
- The `packages/` directory is for shared libraries.
- The `infrastructure/` directory is for Terraform.
- `services/` clearly indicates a standalone service component, distinct from the agent runtimes.

### 3. Client-Side Invocation: HTTP over `requests`
**Decision**: Update Streamlit's `runtime_client.py` to use the standard `requests` library to call the Gateway URL instead of `boto3`.
**Rationale**:
- Removes the need for the Streamlit app to have direct AWS credentials or IAM permissions for AgentCore.
- Standardizes the interface to a RESTful API.
- The Gateway URL will be injected via environment variable (read from SSM by the Streamlit app startup).

### 4. Security & Compliance
**Decision**: Enforce strict Terraform security practices.
**Rationale**:
- **No Committed Plans**: Terraform plan files (`*.tfplan`) contain sensitive data and must never be committed. Validated that `.gitignore` already excludes them.
- **Cleanup Task**: Identified `infrastructure/terraform/envs/dev/tfplan` is currently committed. Added task to remove it from git history/index (`git rm --cached`).
- **Least Privilege**: Gateway Lambda role is scoped strictly to `bedrock-agentcore:InvokeAgentRuntime` and specific SSM paths.

## Alternatives Considered

### A. Cognito Identity Pool + Direct IAM Invoke
- **Description**: Exchange Cognito token for AWS IAM creds in the browser/Streamlit and call AgentCore directly.
- **Rejected**: Does not support the "filtered list" requirement easily (AgentCore doesn't filter based on Cognito groups natively). Harder to audit and control centrally.

### B. API Gateway Lambda Authorizer + Separate Lambdas
- **Description**: Use a dedicated Lambda Authorizer for auth, and separate Lambdas for "List" and "Invoke".
- **Rejected**: Adds complexity (cold starts for multiple functions, more Terraform). The logic is tightly coupled (auth claims determine the list), so a single function is more efficient.

### C. Application Load Balancer (ALB)
- **Description**: Put Streamlit and Gateway behind ALB.
- **Rejected**: Higher cost, less "serverless".

## Unknowns & Clarifications
- **Resolved**: The Gateway will use the `PyJWT` library to validate Cognito tokens (consistent with frontend).
- **Resolved**: The Gateway will use `boto3` to invoke AgentCore Runtime.
