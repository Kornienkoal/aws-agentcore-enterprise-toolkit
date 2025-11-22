# Local Testing Scripts

Three testing methods for developing and testing agents locally without full AWS deployment.

## Quick Start

```bash
# Method 1: Local Development (Recommended)
./scripts/local/start-local-dev.sh warranty-docs

# Method 2: Docker Container
./scripts/local/run-agent-docker.sh warranty-docs "What are the specs for laptop-x1?"

# Method 3: Unit Tests
uv run pytest tests/unit/agents/test_warranty_docs.py -v
```

---

## Testing Methods Comparison

| Method | What Runs Locally | What Runs on AWS | Speed | Auth Required | Use Case |
|--------|------------------|------------------|-------|---------------|----------|
| **1. Local Dev** | Runtime + Tools + UI | Bedrock + Gateway | Fast | ❌ No | Daily development |
| **2. Docker** | Container (Runtime + Tools) | Bedrock + Gateway | Medium | ❌ No | Pre-deployment validation |
| **3. Unit Tests** | Everything (mocked) | Nothing | Very Fast | ❌ No | Tool testing |

---

## Method 1: Local Development Mode (Recommended)

**Best for:** Day-to-day development with instant feedback and full UI.

**Script:** `start-local-dev.sh`

### What It Does

- Starts local runtime HTTP server (port 8000)
- Starts Streamlit UI (port 8501)
- No authentication required
- Streamlit connects to local runtime
- Runtime calls AWS Bedrock models and Gateway tools

### Usage

```bash
# Start everything (runtime server + Streamlit UI)
./scripts/local/start-local-dev.sh warranty-docs

# Custom runtime port
./scripts/local/start-local-dev.sh warranty-docs 8080

# Visit http://localhost:8501 and start chatting
```

### What Runs Where

- ✅ **Local:** Agent runtime code, local tools, Streamlit UI
- ☁️ **AWS:** Bedrock model inference, Gateway tools, SSM configuration

### Advantages

- ✅ No authentication setup needed
- ✅ Fast code iteration
- ✅ Test UI and runtime together
- ✅ See real-time logs
- ✅ Debug with breakpoints

### Logs

```bash
# Runtime logs
tail -f logs/runtime-server.log

# Streamlit logs (shown in terminal)
```

### Stopping

Press `Ctrl+C` - automatically stops both servers

---

## Method 2: Docker Container Testing

**Best for:** Validating Dockerfile, testing in Lambda-like environment.

**Script:** `run-agent-docker.sh`

### What It Does

- Builds Docker image from agent's Dockerfile
- Runs agent in container (Lambda simulation)
- Passes AWS credentials to container
- Returns agent response

### Usage

```bash
# Test with Docker
./scripts/local/run-agent-docker.sh warranty-docs "What are the specs for laptop-x1?"

# Test different prompts
./scripts/local/run-agent-docker.sh warranty-docs "Search documentation for WiFi troubleshooting"
```

### What Runs Where

- ✅ **Local:** Docker container with agent runtime and dependencies
- ☁️ **AWS:** Bedrock model inference, Gateway tools, SSM parameters

### Advantages

- ✅ Simulates Lambda execution environment
- ✅ Tests Dockerfile and dependencies
- ✅ Validates container packaging
- ✅ Catches container-specific issues

### Troubleshooting

```bash
# If AWS credentials fail in container
eval $(aws configure export-credentials --format env)
./scripts/local/run-agent-docker.sh warranty-docs "Test"

# Manual build for debugging
cd agents/warranty-docs
docker build -t test .
docker run --rm -it test /bin/bash
```

---

## Method 3: Unit Tests

**Best for:** Testing individual tool functions without AWS dependencies.

### Usage

```bash
# Run all tests
uv run pytest tests/unit/agents/test_warranty_docs.py -v

# Test specific function
uv run pytest tests/unit/agents/test_warranty_docs.py::TestProductTools::test_get_product_info_success -v

# With coverage
uv run pytest tests/unit/agents/test_warranty_docs.py --cov=agents/warranty-docs --cov-report=term-missing
```

### Advantages

- ✅ Very fast feedback loop
- ✅ No AWS dependencies
- ✅ Test edge cases easily
- ✅ Run in CI/CD

---

## Recommended Workflow

**1. Development Phase** (fastest iteration):
```bash
# Start local dev environment
./scripts/local/start-local-dev.sh warranty-docs

# Edit code, refresh browser to test
# See logs in real-time
```

**2. Pre-Deployment** (validate container):
```bash
# Build and test Docker container
./scripts/local/run-agent-docker.sh warranty-docs "Test in container"
```

**3. Continuous Integration** (unit tests):
```bash
# Run in CI/CD pipeline
uv run pytest tests/unit/agents/test_warranty_docs.py -v --cov
```

---

## Environment Variables

### Local Development Mode

```bash
AGENTCORE_ENV=dev              # Environment name (default: dev)
AWS_REGION=us-east-1           # AWS region (default: us-east-1)
```

### Docker Testing

```bash
AWS_ACCESS_KEY_ID              # Passed to container
AWS_SECRET_ACCESS_KEY          # Passed to container
AWS_SESSION_TOKEN              # Passed to container (if using SSO)
```

---

## Prerequisites

All methods require:

1. **Infrastructure deployed:**
   ```bash
   cd infrastructure/terraform/envs/dev
   terraform init
   terraform apply
   ```

2. **AWS credentials configured:**
   ```bash
   aws sts get-caller-identity
   aws configure get region  # Should be us-east-1
   ```

3. **Dependencies installed:**
   ```bash
   uv sync
   ```

4. **Docker installed** (for Method 2 only)


### 1. `run-agent-local.sh` - Local Runtime Testing

**What it does:**
- Runs agent runtime locally on your machine
- Uses local Python environment (not Docker)
- Calls real Bedrock models via AWS API
- Uses deployed Gateway tools (if authenticated)
- Local monitoring via console logs

**Requirements:**
- `uv sync` completed
- AWS credentials configured
- Infrastructure deployed (for SSM parameters and Gateway)

**Usage:**
```bash
# Basic usage
./scripts/local/run-agent-local.sh warranty-docs "What are the specs for laptop-x1?"

# With environment variables
AGENTCORE_ENV=dev AWS_REGION=us-east-1 \
  ./scripts/local/run-agent-local.sh warranty-docs "Check warranty for laptop-x1"

# Test different agent
./scripts/local/run-agent-local.sh customer-support "Help me with my product"
```

**What runs locally:**
- ✅ Agent runtime (`runtime.py`)
- ✅ Local tools (`tools/*.py`)
- ✅ Configuration loading (`agentcore-common`)
- ✅ Logging and observability (console output)

**What runs on AWS:**
- ☁️ Bedrock model inference
- ☁️ Gateway tools (check-warranty-status, web-search, service-locator)
- ☁️ SSM parameter resolution

---

### 2. `run-agent-docker.sh` - Docker Container Testing

**What it does:**
- Runs agent in Docker container (simulates Lambda environment)
- Uses containerized Python environment
- Calls real Bedrock models via AWS API
- Uses deployed Gateway tools (if authenticated)
- Tests Dockerfile and dependencies

**Requirements:**
- Docker installed and running
- `agents/{agent-name}/Dockerfile` exists
- AWS credentials configured
- Infrastructure deployed

**Usage:**
```bash
# Basic usage
./scripts/local/run-agent-docker.sh warranty-docs "What are the specs for laptop-x1?"

# Build and test custom agent
./scripts/local/run-agent-docker.sh my-agent "Test prompt"
```

**What runs locally:**
- ✅ Docker container with agent runtime
- ✅ Agent runtime (`runtime.py`)
- ✅ Local tools (packaged in container)
- ✅ All Python dependencies (from requirements.txt)

**What runs on AWS:**
- ☁️ Bedrock model inference
- ☁️ Gateway tools
- ☁️ SSM parameter resolution

**When to use:**
- Testing Dockerfile before Lambda deployment
- Verifying dependencies work in container
- Debugging container-specific issues
- Simulating Lambda execution environment

---

### 3. `test-tools-local.sh` - Pure Local Tool Testing

**What it does:**
- Runs unit tests for agent tools
- No AWS calls (fully mocked)
- Fast feedback loop for development
- Coverage reporting available

**Requirements:**
- `uv sync` completed
- Test file exists: `tests/unit/agents/test_{agent_name}.py`

**Usage:**
```bash
# Test warranty-docs tools
./scripts/local/test-tools-local.sh warranty-docs

# Test custom agent tools
./scripts/local/test-tools-local.sh my-agent
```

**What runs locally:**
- ✅ All unit tests
- ✅ Tool functions with mock data
- ✅ Test assertions and validations

**What runs on AWS:**
- ❌ Nothing - fully local

**When to use:**
- Developing new tools
- Quick validation during development
- CI/CD pipeline testing
- Coverage reporting

---

## Comparison Matrix

| Feature | Streamlit UI | Local Runtime | Docker Container | Tool Tests |
|---------|-------------|---------------|------------------|------------|
| **Location** | `services/frontend_streamlit/main.py` | `run-agent-local.sh` | `run-agent-docker.sh` | `test-tools-local.sh` |
| **Agent Runtime** | Deployed Lambda | Local Python | Docker Container | Mocked |
| **Local Tools** | Deployed Lambda | Local Python | Docker Container | Local Python |
| **Gateway Tools** | AWS Gateway | AWS Gateway | AWS Gateway | Mocked |
| **Bedrock Models** | AWS Bedrock | AWS Bedrock | AWS Bedrock | Mocked |
| **Authentication** | Cognito OAuth | None (local only) | None (local only) | N/A |
| **Monitoring** | CloudWatch | Console Logs | Console Logs | Test Output |
| **Speed** | Slow (cold starts) | Fast | Medium | Very Fast |
| **Setup** | Full infra + auth | Minimal | Docker + AWS creds | None |
| **Use Case** | E2E testing | Development | Pre-deployment | Unit testing |

---

## Testing Workflow

### 1. **Development Phase** (fastest iteration)
```bash
# Step 1: Test tools in isolation
./scripts/local/test-tools-local.sh warranty-docs

# Step 2: Test runtime with local tools only
./scripts/local/run-agent-local.sh warranty-docs "Test local tools"
```

### 2. **Pre-Deployment** (validate container)
```bash
# Build and test Docker container
./scripts/local/run-agent-docker.sh warranty-docs "Test in container"
```

### 3. **Integration Testing** (full E2E)
```bash
# Start Streamlit UI
AGENTCORE_ENV=dev AWS_REGION=us-east-1 \
  uv run streamlit run services/frontend_streamlit/main.py

# Test with authentication and Gateway tools
# (Use browser at http://localhost:8501)
```

---

## Environment Variables

All scripts respect these environment variables:

```bash
# Required
export AGENTCORE_ENV=dev          # Environment name (dev, staging, prod)
export AWS_REGION=us-east-1       # AWS region

# Optional (for AWS credentials)
export AWS_PROFILE=default        # AWS profile to use
export AWS_ACCESS_KEY_ID=...      # Explicit credentials
export AWS_SECRET_ACCESS_KEY=...  # (not recommended for local dev)
export AWS_SESSION_TOKEN=...      # For temporary credentials
```

---

## Troubleshooting

### Local Runtime Script

**Issue: "No module named 'runtime'"**
```bash
# Ensure you're running from repo root
cd /path/to/bedrock-agentcore-template
./scripts/local/run-agent-local.sh warranty-docs "Test"
```

**Issue: "SSM parameter not found"**
```bash
# Verify infrastructure is deployed
aws ssm get-parameters-by-path --path /agentcore/dev/ --region us-east-1

# Deploy if needed
cd infrastructure/terraform/envs/dev
terraform apply
```

**Issue: "Bedrock model access denied"**
```bash
# Check model access
aws bedrock list-foundation-models --region us-east-1 | grep claude

# Verify AWS credentials
aws sts get-caller-identity
```

### Docker Script

**Issue: "Docker daemon not running"**
```bash
# Start Docker Desktop (macOS/Windows)
# Or start Docker service (Linux)
sudo systemctl start docker
```

**Issue: "AWS credentials not working in container"**
```bash
# For SSO users, export credentials first
eval $(aws configure export-credentials --format env)
./scripts/local/run-agent-docker.sh warranty-docs "Test"
```

**Issue: "Build fails with dependency errors"**
```bash
# Check Dockerfile and requirements.txt
cat agents/warranty-docs/Dockerfile
cat agents/warranty-docs/requirements.txt

# Test build manually
cd agents/warranty-docs
docker build -t test .
```

### Tool Tests Script

**Issue: "pytest not found"**
```bash
# Install dev dependencies
uv sync
```

**Issue: "Test file not found"**
```bash
# Verify test file exists
ls tests/unit/agents/test_warranty_docs.py

# Create if needed (see agents/README.md)
```

---

## Advanced Usage

### Custom Test Payloads

```bash
# Create custom test script
cat > test_custom.py << 'EOF'
import asyncio
import sys
from types import SimpleNamespace

sys.path.insert(0, "agents/warranty-docs")
import runtime

async def test():
    # Custom payload with context
    payload = {
        "prompt": "Check warranty for laptop-x1",
        "user_id": "test-user-123",
        "session_id": "session-456"
    }

    # Mock context with auth header
    context = SimpleNamespace(
        request_headers={"Authorization": "Bearer mock-token"}
    )

    result = await runtime.invoke(payload, context)
    print(result)

asyncio.run(test())
EOF

# Run custom test
AGENTCORE_ENV=dev AWS_REGION=us-east-1 uv run python test_custom.py
```

### Debugging with Breakpoints

```bash
# Add breakpoint in agent code
# agents/warranty-docs/runtime.py:
# import pdb; pdb.set_trace()

# Run with debugger
AGENTCORE_ENV=dev AWS_REGION=us-east-1 \
  uv run python -m pdb -c continue \
  <(cat <<'EOF'
import asyncio
import sys
from types import SimpleNamespace

sys.path.insert(0, "agents/warranty-docs")
import runtime

asyncio.run(runtime.invoke({"prompt": "test"}, SimpleNamespace(request_headers={})))
EOF
)
```

### Load Testing

```bash
# Test multiple prompts in sequence
for i in {1..10}; do
  echo "Test $i"
  ./scripts/local/run-agent-local.sh warranty-docs "Test prompt $i"
  sleep 2
done
```

---

## Performance Benchmarks

Typical execution times on M1 MacBook Pro:

| Method | Cold Start | Warm Start | Total (10 calls) |
|--------|-----------|------------|------------------|
| Streamlit UI | 15-20s | 8-12s | ~120s |
| Local Runtime | 0s | 6-10s | ~80s |
| Docker Container | 3-5s | 6-10s | ~85s |
| Tool Tests | 0s | 0.3-0.6s | ~5s |

*Note: Times include Bedrock API latency (4-8s per call)*

---

## Next Steps

1. **Start with tool tests** - fastest feedback
2. **Use local runtime** - for development
3. **Test in Docker** - before deployment
4. **Full E2E with Streamlit** - final validation

For more details, see:
- `agents/README.md` - Full testing documentation
- `agents/{agent-name}/README.md` - Agent-specific guides
- `infrastructure/terraform/README.md` - Infrastructure setup
