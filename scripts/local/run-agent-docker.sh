#!/usr/bin/env bash
# Run agent in Docker container (simulates Lambda environment)
# Usage: ./scripts/local/run-agent-docker.sh warranty-docs "What are the specs for laptop-x1?"

set -e

AGENT_NAME="${1:-warranty-docs}"
PROMPT="${2:-Hello, how can you help me?}"

echo "🐳 Running agent in Docker: $AGENT_NAME"
echo "📝 Prompt: $PROMPT"
echo ""

# Set environment
export AGENTCORE_ENV="${AGENTCORE_ENV:-dev}"
export AWS_REGION="${AWS_REGION:-us-east-1}"

# Build Docker image
echo "📦 Building Docker image..."
docker build -t "agentcore-${AGENT_NAME}-local" \
  -f "agents/${AGENT_NAME}/Dockerfile" \
  .  # Build from repo root with full context

# Get AWS credentials for container (supports SSO)
AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id 2>/dev/null || echo "")
AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key 2>/dev/null || echo "")
AWS_SESSION_TOKEN=$(aws configure get aws_session_token 2>/dev/null || echo "")

# If using SSO, try exporting current session credentials to env
if [ -z "$AWS_ACCESS_KEY_ID" ]; then
  # Export credentials from selected profile if available; fallback to default
  if command -v aws >/dev/null 2>&1; then
    if aws --version >/dev/null 2>&1; then
      PROFILE_ARG=""
      if [ -n "$AWS_PROFILE" ]; then PROFILE_ARG="--profile $AWS_PROFILE"; fi
      # export-credentials emits shell-compatible env lines; eval to import
      CREDS_OUTPUT=$(aws configure export-credentials $PROFILE_ARG --format env 2>/dev/null || true)
      if [ -n "$CREDS_OUTPUT" ]; then eval "$CREDS_OUTPUT"; fi
    fi
  fi
  # Re-read values from environment (set by export-credentials or user)
  AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
  AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"
  AWS_SESSION_TOKEN="${AWS_SESSION_TOKEN:-}"
fi

echo "� Attempting to acquire Gateway bearer token (best-effort)..."
# Respect pre-set AUTH_TOKEN; otherwise, try M2M via Cognito Client Credentials using SSM values
AUTH_TOKEN="${AUTH_TOKEN:-}"
if [ -z "$AUTH_TOKEN" ]; then
  AUTH_TOKEN=$(
    (
      CLIENT_ID=$(aws ssm get-parameter --name "/agentcore/${AGENTCORE_ENV}/identity/client_id" --query 'Parameter.Value' --output text 2>/dev/null) &&
      CLIENT_SECRET=$(aws ssm get-parameter --name "/agentcore/${AGENTCORE_ENV}/identity/client_secret" --with-decryption --query 'Parameter.Value' --output text 2>/dev/null) &&
      DOMAIN=$(aws ssm get-parameter --name "/agentcore/${AGENTCORE_ENV}/identity/domain" --query 'Parameter.Value' --output text 2>/dev/null) &&
      curl -s -X POST "https://${DOMAIN}.auth.${AWS_REGION}.amazoncognito.com/oauth2/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -u "${CLIENT_ID}:${CLIENT_SECRET}" \
        -d "grant_type=client_credentials" | \
      python3 - <<'PY'
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('access_token', ''))
except Exception:
    print('')
PY
    ) || echo ""
  )
fi

if [ -n "$AUTH_TOKEN" ]; then
  echo "✅ AUTH_TOKEN acquired (${#AUTH_TOKEN} chars)"
else
  echo "ℹ️  No AUTH_TOKEN available; Gateway tools will be skipped"
fi

echo "�🚀 Running container..."
echo "------------------------------------------------------------"

# Run container with AWS credentials
docker run --rm \
  -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
  -e AWS_REGION="$AWS_REGION" \
  -e AGENTCORE_ENV="$AGENTCORE_ENV" \
  -e AUTH_TOKEN="$AUTH_TOKEN" \
  "agentcore-${AGENT_NAME}-local" \
  python -c "
import asyncio
import sys
from runtime import invoke
from types import SimpleNamespace
import os

async def test():
    payload = {'prompt': '''$PROMPT'''}
    token = os.environ.get('AUTH_TOKEN')
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    context = SimpleNamespace(request_headers=headers)
    result = await invoke(payload, context)
    print('=' * 60)
    print('Agent Response:')
    print('=' * 60)
    print(result)
    return result

asyncio.run(test())
"

echo ""
echo "✅ Docker test completed"
