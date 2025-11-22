# Quickstart: Frontend Gateway

## Prerequisites
- Deployed `frontend-gateway` Terraform module.
- Cognito User Pool with `allowedAgents` custom attribute (mapped from groups).

## Local Development

1. **Install Dependencies**:
   ```bash
   cd services/frontend-gateway
   uv sync
   ```

2. **Run Tests**:
   ```bash
   uv run pytest
   ```

3. **Run Streamlit with Gateway**:
   ```bash
   export AGENTCORE_GATEWAY_URL="https://<api-id>.execute-api.<region>.amazonaws.com"
   uv run streamlit run services/frontend_streamlit/main.py
   ```

## Deployment

> **Apple Silicon note:** The Terraform module now forces Docker to build with
> `--platform=linux/amd64`, so the packaged dependencies always match the
> Lambda's x86_64 runtime. If you copy this pattern elsewhere, make sure your
> Docker builds also target `linux/amd64` (either via
> `docker_additional_options` or `DOCKER_DEFAULT_PLATFORM`).

1. **Apply Terraform**:
   ```bash
   cd infrastructure/terraform/envs/dev
   terraform apply -target=module.frontend_gateway
   ```

2. **Verify**:
   - Check SSM parameter `/agentcore/dev/frontend-gateway/api_endpoint`.
   - Curl the endpoint with a valid Cognito token:
     ```bash
     curl -H "Authorization: Bearer $TOKEN" $GATEWAY_URL/agents
     ```
